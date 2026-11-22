use axum::{
    extract::{Query, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;

use crate::models::delivery::{CandidateDeliveryRequest, CandidateDeliveryResponse};
use crate::models::search::{
    SearchResponse, SearchSuggestionsResponse, SelectedResultRequest, SelectedResultResponse,
};
use crate::services::telegram_delivery::{TelegramDeliveryError, TelegramDeliveryService};
use crate::services::telegram_search::{TelegramSearchError, TelegramSearchService};

#[derive(Debug, Deserialize)]
pub struct SearchQueryParams {
    pub q: Option<String>,
    pub query: Option<String>,
    pub page: Option<i64>,
    pub max_pages: Option<i64>,
}

#[derive(Debug, Deserialize)]
pub struct SuggestionQueryParams {
    pub q: Option<String>,
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize)]
pub struct VersionsQueryParams {
    pub title: String,
    pub max_pages: Option<i64>,
}

pub struct SearchApiState {
    pub search_service: Arc<TelegramSearchService>,
    pub delivery_service: Arc<TelegramDeliveryService>,
    pub axum_port: u16,
}

fn map_search_error(err: TelegramSearchError) -> (StatusCode, Json<serde_json::Value>) {
    match err {
        TelegramSearchError::NotConnected => (
            StatusCode::UNAUTHORIZED,
            Json(json!({
                "detail": "Your Telegram account is not connected. Please connect your account in Cineforge settings to search."
            })),
        ),
        TelegramSearchError::RateLimited(secs) => (
            StatusCode::TOO_MANY_REQUESTS,
            Json(json!({
                "detail": format!("Telegram rate limit reached. Please wait {} seconds before trying again.", secs)
            })),
        ),
        TelegramSearchError::Timeout(bot, secs) => (
            StatusCode::GATEWAY_TIMEOUT,
            Json(json!({
                "detail": format!("Telegram bot @{} did not respond within {} seconds. It may be offline or rate-limiting.", bot, secs)
            })),
        ),
        TelegramSearchError::General(msg) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "detail": msg })),
        ),
    }
}

fn map_delivery_error(err: TelegramDeliveryError) -> (StatusCode, Json<serde_json::Value>) {
    match err {
        TelegramDeliveryError::NotConnected => (
            StatusCode::UNAUTHORIZED,
            Json(json!({
                "detail": "Your Telegram account is not connected. Please connect your account in Cineforge settings to start streaming."
            })),
        ),
        TelegramDeliveryError::ChannelRequirement(req) => (
            StatusCode::FORBIDDEN,
            Json(json!({
                "detail": format!("Channel membership required: {}", req.message),
                "channel_requirement": req
            })),
        ),
        TelegramDeliveryError::Timeout(bot, secs) => (
            StatusCode::GATEWAY_TIMEOUT,
            Json(json!({
                "detail": format!("Bot @{} did not deliver media within {} seconds. It may be offline or rate-limiting.", bot, secs)
            })),
        ),
        TelegramDeliveryError::RateLimited(secs) => (
            StatusCode::TOO_MANY_REQUESTS,
            Json(json!({
                "detail": format!("Telegram rate limit reached. Please wait {} seconds before trying again.", secs)
            })),
        ),
        TelegramDeliveryError::General(msg) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "detail": msg })),
        ),
    }
}

async fn search_movies_handler(
    State(state): State<Arc<SearchApiState>>,
    Query(params): Query<SearchQueryParams>,
) -> Result<Json<SearchResponse>, (StatusCode, Json<serde_json::Value>)> {
    let q = params
        .q
        .or(params.query)
        .unwrap_or_default()
        .trim()
        .to_string();

    let page = params.page.unwrap_or(1).clamp(1, 10);
    let max_pages = params.max_pages.unwrap_or(2).clamp(1, 5);

    state
        .search_service
        .search_movies(&q, page, max_pages)
        .await
        .map(Json)
        .map_err(map_search_error)
}

async fn get_suggestions_handler(
    State(state): State<Arc<SearchApiState>>,
    Query(params): Query<SuggestionQueryParams>,
) -> Json<SearchSuggestionsResponse> {
    let q = params.q.unwrap_or_default().trim().to_string();
    let limit = params.limit.unwrap_or(5).clamp(1, 10);

    Json(state.search_service.get_suggestions(&q, limit).await)
}

async fn select_candidate_handler(
    State(state): State<Arc<SearchApiState>>,
    Json(payload): Json<SelectedResultRequest>,
) -> Result<Json<SelectedResultResponse>, (StatusCode, Json<serde_json::Value>)> {
    state
        .search_service
        .select_candidate(&payload)
        .await
        .map(Json)
        .map_err(map_search_error)
}

async fn find_versions_handler(
    State(state): State<Arc<SearchApiState>>,
    Query(params): Query<VersionsQueryParams>,
) -> Result<Json<SearchResponse>, (StatusCode, Json<serde_json::Value>)> {
    let title = params.title.trim().to_string();
    let max_pages = params.max_pages.unwrap_or(3).clamp(1, 5);

    state
        .search_service
        .search_movies(&title, 1, max_pages)
        .await
        .map(Json)
        .map_err(map_search_error)
}

async fn deliver_candidate_handler(
    State(state): State<Arc<SearchApiState>>,
    Json(payload): Json<CandidateDeliveryRequest>,
) -> Result<Json<CandidateDeliveryResponse>, (StatusCode, Json<serde_json::Value>)> {
    state
        .delivery_service
        .deliver_candidate(&payload, state.axum_port)
        .await
        .map(Json)
        .map_err(map_delivery_error)
}

/// Creates the Axum router for search, candidate delivery, and result selection endpoints.
pub fn create_search_router(
    search_service: Arc<TelegramSearchService>,
    delivery_service: Arc<TelegramDeliveryService>,
    axum_port: u16,
) -> Router {
    let state = Arc::new(SearchApiState {
        search_service,
        delivery_service,
        axum_port,
    });

    Router::new()
        .route("/search", get(search_movies_handler))
        .route("/search/suggestions", get(get_suggestions_handler))
        .route("/search/select", post(select_candidate_handler))
        .route("/search/versions", get(find_versions_handler))
        .route("/search/deliver", post(deliver_candidate_handler))
        .with_state(state)
}
