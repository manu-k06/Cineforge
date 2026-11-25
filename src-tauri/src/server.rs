use axum::{
    http::{HeaderValue, Method},
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::oneshot;
use tower_http::cors::CorsLayer;

use crate::api::metadata::create_metadata_router;
use crate::api::search::create_search_router;
use crate::api::stream::create_stream_router;
use crate::api::telegram::create_telegram_auth_router_with_services;
use crate::config::ServerConfig;
use crate::services::bot_provisioning::BotProvisioningService;
use crate::services::streamer_sidecar::StreamerSidecarService;
use crate::services::telegram_auth::TelegramAuthService;
use crate::services::telegram_delivery::TelegramDeliveryService;
use crate::services::telegram_search::TelegramSearchService;
use crate::services::tmdb::{TmdbConfig, TmdbService};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendInfo {
    pub status: String,
    pub host: String,
    pub port: u16,
    pub api_url: String,
    pub version: String,
    pub engine: String,
}

pub struct RunningServer {
    pub info: BackendInfo,
    pub shutdown_tx: Option<oneshot::Sender<()>>,
}

/// Handler for GET /health and GET /api/health
async fn health_check() -> Json<Value> {
    Json(serde_json::json!({
        "status": "ok",
        "service": "cineforge-backend",
        "engine": "rust-axum",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

/// Builds the restricted CORS layer for desktop and local dev access.
fn build_restricted_cors() -> CorsLayer {
    let allowed_origins = [
        "tauri://localhost".parse::<HeaderValue>().unwrap(),
        "https://tauri.localhost".parse::<HeaderValue>().unwrap(),
        "http://localhost:5173".parse::<HeaderValue>().unwrap(),
        "http://127.0.0.1:5173".parse::<HeaderValue>().unwrap(),
        "http://localhost:3000".parse::<HeaderValue>().unwrap(),
        "http://127.0.0.1:3000".parse::<HeaderValue>().unwrap(),
    ];

    CorsLayer::new()
        .allow_origin(allowed_origins)
        .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
        .allow_headers(tower_http::cors::Any)
}

/// Builds the Axum router with provided services.
pub fn create_router_with_services(
    tmdb_service: Arc<TmdbService>,
    telegram_auth_service: Arc<TelegramAuthService>,
    telegram_search_service: Arc<TelegramSearchService>,
    telegram_delivery_service: Arc<TelegramDeliveryService>,
    streamer_sidecar_service: Arc<StreamerSidecarService>,
    bot_provisioning_service: Arc<BotProvisioningService>,
    axum_port: u16,
) -> Router {
    Router::new()
        .route("/health", get(health_check))
        .route("/api/health", get(health_check))
        .nest("/api/metadata", create_metadata_router(tmdb_service))
        .nest(
            "/api/telegram/auth",
            create_telegram_auth_router_with_services(
                telegram_auth_service,
                Arc::clone(&streamer_sidecar_service),
                bot_provisioning_service,
            ),
        )
        .nest(
            "/api",
            create_search_router(telegram_search_service, telegram_delivery_service, axum_port),
        )
        .merge(create_stream_router(streamer_sidecar_service))
        .layer(build_restricted_cors())
}

/// Helper for tests to build a router with mock streamer, provisioning, and delivery services.
pub fn create_test_router_with_services(
    tmdb_service: Arc<TmdbService>,
    telegram_auth_service: Arc<TelegramAuthService>,
    telegram_search_service: Arc<TelegramSearchService>,
) -> Router {
    let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
    let provisioning = Arc::new(BotProvisioningService::new_mock(
        88888888,
        "cf_mock_streamer_bot",
        "mock_token",
    ));
    let delivery = Arc::new(TelegramDeliveryService::new(
        Arc::clone(&telegram_auth_service),
        Arc::clone(&sidecar),
        Arc::clone(&provisioning),
    ));
    create_router_with_services(
        tmdb_service,
        telegram_auth_service,
        telegram_search_service,
        delivery,
        sidecar,
        provisioning,
        59199,
    )
}

/// Builds the Axum router with health, metadata, telegram auth, search, delivery, and streaming endpoints.
pub fn create_router(bound_port: u16) -> (Router, Arc<StreamerSidecarService>) {
    crate::config::load_env_files();
    let tmdb_config = TmdbConfig::default();
    let tmdb_service = Arc::new(TmdbService::new(tmdb_config));
    let telegram_auth_service = Arc::new(TelegramAuthService::new());
    let telegram_search_service = Arc::new(TelegramSearchService::new(Arc::clone(&telegram_auth_service)));
    let streamer_sidecar_service = Arc::new(StreamerSidecarService::new());
    let bot_provisioning_service = Arc::new(BotProvisioningService::new());
    let telegram_delivery_service = Arc::new(TelegramDeliveryService::new(
        Arc::clone(&telegram_auth_service),
        Arc::clone(&streamer_sidecar_service),
        Arc::clone(&bot_provisioning_service),
    ));

    let router = create_router_with_services(
        tmdb_service,
        telegram_auth_service,
        telegram_search_service,
        telegram_delivery_service,
        Arc::clone(&streamer_sidecar_service),
        bot_provisioning_service,
        bound_port,
    );

    (router, streamer_sidecar_service)
}

/// Starts the embedded Axum HTTP service bound strictly to loopback (127.0.0.1).
/// Uses an ephemeral port if port 0 is specified in config.
pub async fn start_server(config: ServerConfig) -> Result<RunningServer, Box<dyn std::error::Error + Send + Sync>> {
    let bind_addr = SocketAddr::from((config.host, config.port));
    let listener = TcpListener::bind(bind_addr).await?;
    let local_addr = listener.local_addr()?;
    let bound_port = local_addr.port();

    let info = BackendInfo {
        status: "online".to_string(),
        host: config.host.to_string(),
        port: bound_port,
        api_url: format!("http://{}:{}", config.host, bound_port),
        version: env!("CARGO_PKG_VERSION").to_string(),
        engine: "rust-axum".to_string(),
    };

    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();
    let (router, streamer_sidecar) = create_router(bound_port);

    // Note: Do not eagerly start the Go streamer sidecar without a personal bot token.
    // It is started on-demand with the user's runtime personal bot token during media delivery.
    let sidecar_for_shutdown = Arc::clone(&streamer_sidecar);

    // Spawn server in a background Tokio task with graceful shutdown
    tokio::spawn(async move {
        log::info!("Local Axum API server listening on {}", local_addr);
        if let Err(err) = axum::serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
                log::info!("Local Axum API server received shutdown signal.");
                if let Err(err) = sidecar_for_shutdown.stop().await {
                    log::warn!("Error stopping Go streamer sidecar on shutdown: {err}");
                }
            })
            .await
        {
            log::error!("Local Axum API server error: {}", err);
        }
    });

    Ok(RunningServer {
        info,
        shutdown_tx: Some(shutdown_tx),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::to_bytes;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_health_check_endpoint() {
        let (app, _) = create_router(8080);
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["status"], "ok");
        assert_eq!(json["engine"], "rust-axum");
    }

    #[tokio::test]
    async fn test_api_health_endpoint() {
        let (app, _) = create_router(8080);
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/api/health")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_metadata_trending_endpoint_returns_real_or_fallback_movies() {
        let (app, _) = create_router(8080);
        let res_trending = app
            .oneshot(
                Request::builder()
                    .uri("/api/metadata/trending?page=1")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res_trending.status(), StatusCode::OK);
        let body_t = to_bytes(res_trending.into_body(), 1024 * 64).await.unwrap();
        let trending_json: serde_json::Value = serde_json::from_slice(&body_t).unwrap();
        assert_eq!(trending_json["page"], 1);
        let results = trending_json["results"].as_array().expect("results array");
        assert!(!results.is_empty(), "trending results must not be empty");
        assert!(results[0]["title"].is_string());
    }

    #[tokio::test]
    async fn test_metadata_status_endpoint() {
        let (app, _) = create_router(8080);
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/api/metadata/status")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json.get("status").is_some());
        assert!(json.get("configured").is_some());
    }

    #[tokio::test]
    async fn test_metadata_movie_fallback_when_unconfigured() {
        let tmdb_config = TmdbConfig {
            proxy_url: None,
            supabase_anon_key: None,
            direct_tmdb_key: None,
        };
        let tmdb_service = Arc::new(TmdbService::new(tmdb_config));
        let telegram_auth_service = Arc::new(TelegramAuthService::new());
        let telegram_search_service = Arc::new(TelegramSearchService::new(Arc::clone(&telegram_auth_service)));
        let app = create_test_router_with_services(tmdb_service, telegram_auth_service, telegram_search_service);

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/api/metadata/movie?title=Inception%202010%201080p")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["title"], "Inception");
        assert_eq!(json["year"], "2010");
        assert_eq!(json["source"], "fallback");
    }

    #[tokio::test]
    async fn test_metadata_movie_missing_title() {
        let (app, _) = create_router(8080);
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/api/metadata/movie")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_metadata_trending_fallback_when_unconfigured() {
        let tmdb_config = TmdbConfig {
            proxy_url: None,
            supabase_anon_key: None,
            direct_tmdb_key: None,
        };
        let tmdb_service = Arc::new(TmdbService::new(tmdb_config));
        let telegram_auth_service = Arc::new(TelegramAuthService::new());
        let telegram_search_service = Arc::new(TelegramSearchService::new(Arc::clone(&telegram_auth_service)));
        let app = create_test_router_with_services(tmdb_service, telegram_auth_service, telegram_search_service);

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/api/metadata/trending?page=1")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), 1024 * 32).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["page"], 1);
        let results = json["results"].as_array().unwrap();
        assert!(!results.is_empty());
        assert_eq!(results[0]["title"], "Inception");
    }

    #[tokio::test]
    async fn test_start_server_ephemeral_port_and_shutdown() {
        let config = ServerConfig {
            host: std::net::Ipv4Addr::new(127, 0, 0, 1),
            port: 0,
            app_name: "Test Server".to_string(),
            environment: "test".to_string(),
        };

        let running = start_server(config).await.expect("server failed to start");
        assert_eq!(running.info.host, "127.0.0.1");
        assert!(running.info.port > 0);
        assert!(running.info.api_url.starts_with("http://127.0.0.1:"));

        // Trigger shutdown cleanly
        if let Some(tx) = running.shutdown_tx {
            let _ = tx.send(());
        }
    }

    #[tokio::test]
    async fn test_server_telegram_auth_endpoints() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let telegram = Arc::new(TelegramAuthService::new_mock());
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        // GET /api/telegram/auth/status
        let res_status = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/telegram/auth/status")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_status.status(), StatusCode::OK);
        let body = to_bytes(res_status.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["connected"], false);
        assert_eq!(json["status"], "disconnected");

        // POST /api/telegram/auth/qr/start
        let res_qr = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/telegram/auth/qr/start")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_qr.status(), StatusCode::OK);
        let qr_body = to_bytes(res_qr.into_body(), 1024 * 16).await.unwrap();
        let qr_json: serde_json::Value = serde_json::from_slice(&qr_body).unwrap();
        assert!(qr_json["qr_uri"].as_str().unwrap().starts_with("tg://login?token="));

        // GET /api/telegram/auth/qr/check
        let res_check = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/telegram/auth/qr/check")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_check.status(), StatusCode::OK);
        let check_body = to_bytes(res_check.into_body(), 1024 * 16).await.unwrap();
        let check_json: serde_json::Value = serde_json::from_slice(&check_body).unwrap();
        assert_eq!(check_json["status"], "connected");
        assert_eq!(check_json["user"]["first_name"], "MockUser");

        // POST /api/telegram/auth/disconnect
        let res_disc = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/telegram/auth/disconnect")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_disc.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_search_endpoint_when_disconnected_returns_401() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let telegram = Arc::new(TelegramAuthService::new_mock()); // disconnected by default
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let res = app
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=Inception")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::UNAUTHORIZED);
        let body = to_bytes(res.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json["detail"].as_str().unwrap().contains("not connected"));
    }

    #[tokio::test]
    async fn test_search_endpoint_when_connected_returns_candidates_and_title_groups() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: Some("tester".to_string()),
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let res = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=Inception&page=1&max_pages=2")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = to_bytes(res.into_body(), 1024 * 64).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let candidates = json["candidates"].as_array().expect("candidates array");
        assert!(!candidates.is_empty(), "candidates must not be empty");
        assert_eq!(json["query"], "Inception");

        // Verify title groups
        let title_groups = json["title_groups"].as_object().expect("title groups object");
        assert!(!title_groups.is_empty());

        // Verify pagination
        let pagination = &json["pagination"];
        assert_eq!(pagination["current_page"], 2); // aggregated 2 pages
        assert_eq!(pagination["total_pages"], 3);
        assert_eq!(pagination["total_results"], 15);
    }

    #[tokio::test]
    async fn test_search_endpoint_timeout_and_rate_limit_handling() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        // 1. Timeout query
        let res_timeout = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=test_timeout")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_timeout.status(), StatusCode::GATEWAY_TIMEOUT);

        // 2. Rate limited query
        let res_rate = app
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=test_rate_limit")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_rate.status(), StatusCode::TOO_MANY_REQUESTS);
    }

    #[tokio::test]
    async fn test_search_endpoint_fsub_channel_requirement() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let res = app
            .oneshot(
                Request::builder()
                    .uri("/api/search?q=test_fsub")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = to_bytes(res.into_body(), 1024 * 32).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let req = &json["channel_requirement"];
        assert_eq!(req["required"], true);
        assert!(req["invite_url"].as_str().unwrap().contains("join_cineforge_channel"));
    }

    #[tokio::test]
    async fn test_search_select_endpoint_resolves_selection() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let payload = serde_json::json!({
            "candidate_id": "cand-1234567890abcdef",
            "source_bot": "Spoty_xbot",
            "source_message_id": 105,
            "callback_data": "dl_cand_1080p",
            "type": "callback"
        });

        let res = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/search/select")
                    .header("Content-Type", "application/json")
                    .body(axum::body::Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = to_bytes(res.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["status"], "resolved");
        assert_eq!(json["resolved_type"], "callback");
        assert_eq!(json["target_bot"], "Spoty_xbot");
    }

    #[tokio::test]
    async fn test_search_suggestions_endpoint() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let telegram = Arc::new(TelegramAuthService::new_mock());
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let res = app
            .oneshot(
                Request::builder()
                    .uri("/api/search/suggestions?q=Incep")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = to_bytes(res.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let suggestions = json["suggestions"].as_array().expect("suggestions array");
        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0]["title"], "Inception");
    }

    #[tokio::test]
    async fn test_candidate_delivery_unauthorized_when_not_connected() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let telegram = Arc::new(TelegramAuthService::new_mock()); // disconnected
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let payload = serde_json::json!({
            "candidate_id": "cand_1",
            "source_bot": "Spoty_xbot",
            "source_message_id": 105,
            "candidate_title": "Inception (2010)",
            "callback_data": "dl_1080p"
        });

        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/search/deliver")
                    .header("Content-Type", "application/json")
                    .body(axum::body::Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::UNAUTHORIZED);
        let body = to_bytes(res.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json["detail"].as_str().unwrap().contains("not connected"));
    }

    #[tokio::test]
    async fn test_candidate_delivery_success_returns_local_streaming_url() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: Some("tester".to_string()),
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let payload = serde_json::json!({
            "candidate_id": "cand_1080p_mp4",
            "source_bot": "Spoty_xbot",
            "source_message_id": 105,
            "candidate_title": "Inception (2010)",
            "callback_data": "dl_1080p"
        });

        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/search/deliver")
                    .header("Content-Type", "application/json")
                    .body(axum::body::Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = to_bytes(res.into_body(), 1024 * 32).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["success"], true);
        assert_eq!(json["container"], "mp4");
        assert_eq!(json["browser_playable"], true);
        assert_eq!(json["playback_mode"], "browser");
        let stream_url = json["stream_url"].as_str().expect("stream_url string");
        assert!(stream_url.starts_with("http://127.0.0.1:"));
        assert!(stream_url.contains("/api/stream/"));
        assert!(stream_url.contains("hash="));
    }

    #[tokio::test]
    async fn test_candidate_delivery_fsub_channel_requirement() {
        let tmdb = Arc::new(TmdbService::new(TmdbConfig::default()));
        let user = crate::models::telegram::TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let telegram = Arc::new(TelegramAuthService::new_mock_connected(user));
        let search = Arc::new(TelegramSearchService::new(Arc::clone(&telegram)));
        let app = create_test_router_with_services(tmdb, telegram, search);

        let payload = serde_json::json!({
            "candidate_id": "cand_fsub_locked",
            "source_bot": "Spoty_xbot",
            "source_message_id": 106,
            "candidate_title": "Locked Movie",
            "callback_data": "dl_locked"
        });

        let res = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/search/deliver")
                    .header("Content-Type", "application/json")
                    .body(axum::body::Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::FORBIDDEN);
        let body = to_bytes(res.into_body(), 1024 * 16).await.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json["channel_requirement"].is_object());
        assert_eq!(json["channel_requirement"]["required"], true);
    }
}
