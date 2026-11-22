use axum::{
    body::Body,
    extract::{Path as AxumPath, Query, State},
    http::{header, HeaderMap, HeaderValue, StatusCode},
    response::Response,
    routing::get,
    Router,
};
use futures_util::TryStreamExt;
use serde::Deserialize;
use std::sync::Arc;

use crate::services::streamer_sidecar::StreamerSidecarService;

#[derive(Debug, Deserialize)]
pub struct StreamQueryParams {
    pub hash: Option<String>,
    pub d: Option<String>,
    pub raw: Option<String>,
}

pub struct StreamApiState {
    pub sidecar: Arc<StreamerSidecarService>,
    pub client: reqwest::Client,
}

/// Handles progressive byte-range media streaming proxying directly to the Go streamer sidecar.
pub async fn stream_media_handler(
    State(state): State<Arc<StreamApiState>>,
    AxumPath(message_id): AxumPath<i64>,
    Query(params): Query<StreamQueryParams>,
    headers: HeaderMap,
) -> Result<Response, (StatusCode, String)> {
    let port = state.sidecar.get_port().await.ok_or_else(|| {
        (
            StatusCode::SERVICE_UNAVAILABLE,
            "Go media streamer sidecar is not running.".to_string(),
        )
    })?;

    let hash = params.hash.unwrap_or_default();
    let mut upstream_url = format!("http://127.0.0.1:{port}/stream/{message_id}?hash={hash}");
    if let Some(d) = params.d {
        upstream_url.push_str(&format!("&d={d}"));
    }
    if let Some(raw) = params.raw {
        upstream_url.push_str(&format!("&raw={raw}"));
    }

    let mut req_builder = state.client.get(&upstream_url);

    // Forward Range header for video timeline seeking / scrubbing
    if let Some(range_val) = headers.get(header::RANGE) {
        if let Ok(range_str) = range_val.to_str() {
            req_builder = req_builder.header(header::RANGE, range_str);
        }
    }

    let upstream_resp = req_builder.send().await.map_err(|e| {
        (
            StatusCode::BAD_GATEWAY,
            format!("Failed to connect to media streamer: {e}"),
        )
    })?;

    let status = upstream_resp.status();
    let resp_headers = upstream_resp.headers().clone();

    // Convert upstream chunked byte stream into Axum streaming body
    let body_stream = upstream_resp.bytes_stream().map_err(|e| {
        std::io::Error::new(std::io::ErrorKind::Other, e)
    });
    let body = Body::from_stream(body_stream);

    let mut response = Response::builder();

    if status == reqwest::StatusCode::PARTIAL_CONTENT {
        response = response.status(StatusCode::PARTIAL_CONTENT);
    } else if status.is_success() {
        response = response.status(StatusCode::OK);
    } else {
        response = response.status(StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::BAD_GATEWAY));
    }

    // Forward critical media streaming headers
    if let Some(val) = resp_headers.get(header::CONTENT_RANGE) {
        response = response.header(header::CONTENT_RANGE, val);
    }
    if let Some(val) = resp_headers.get(header::CONTENT_LENGTH) {
        response = response.header(header::CONTENT_LENGTH, val);
    }
    if let Some(val) = resp_headers.get(header::CONTENT_TYPE) {
        response = response.header(header::CONTENT_TYPE, val);
    } else {
        response = response.header(header::CONTENT_TYPE, "video/mp4");
    }
    if let Some(val) = resp_headers.get(header::CONTENT_DISPOSITION) {
        response = response.header(header::CONTENT_DISPOSITION, val);
    }

    // Always signal byte-range capabilities and permissive CORS for local desktop playback
    response = response
        .header(header::ACCEPT_RANGES, HeaderValue::from_static("bytes"))
        .header(header::ACCESS_CONTROL_ALLOW_ORIGIN, HeaderValue::from_static("*"))
        .header(header::ACCESS_CONTROL_ALLOW_METHODS, HeaderValue::from_static("GET, HEAD, OPTIONS"))
        .header(
            header::ACCESS_CONTROL_EXPOSE_HEADERS,
            HeaderValue::from_static("Content-Range, Content-Length, Accept-Ranges, Content-Type, Content-Disposition"),
        );

    response.body(body).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to assemble stream response: {e}"),
        )
    })
}

/// Creates the router for progressive media streaming.
pub fn create_stream_router(sidecar: Arc<StreamerSidecarService>) -> Router {
    let state = Arc::new(StreamApiState {
        sidecar,
        client: reqwest::Client::builder()
            .timeout(Duration::from_secs(60))
            .build()
            .unwrap_or_default(),
    });

    Router::new()
        .route("/stream/{message_id}", get(stream_media_handler).head(stream_media_handler))
        .route("/api/stream/{message_id}", get(stream_media_handler).head(stream_media_handler))
        .with_state(state)
}

use std::time::Duration;
