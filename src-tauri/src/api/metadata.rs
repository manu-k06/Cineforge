use axum::{
    extract::{Query, State},
    http::StatusCode,
    routing::get,
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;

use crate::models::metadata::{MetadataStatusResponse, MovieMetadata, TrendingMoviesResponse};
use crate::services::tmdb::TmdbService;

#[derive(Debug, Deserialize)]
pub struct MovieQuery {
    pub title: Option<String>,
    pub year: Option<i32>,
}

#[derive(Debug, Deserialize)]
pub struct TrendingQuery {
    #[serde(default = "default_time_window")]
    pub time_window: String,
    #[serde(default = "default_page")]
    pub page: i64,
}

fn default_time_window() -> String {
    "week".to_string()
}

fn default_page() -> i64 {
    1
}

#[derive(Debug, Deserialize)]
pub struct PageQuery {
    #[serde(default = "default_page")]
    pub page: i64,
}

#[derive(Debug, Deserialize)]
pub struct DiscoverQuery {
    #[serde(default = "default_language")]
    pub language: String,
    #[serde(default = "default_sort_by")]
    pub sort_by: String,
    #[serde(default = "default_page")]
    pub page: i64,
}

fn default_language() -> String {
    "ml".to_string()
}

fn default_sort_by() -> String {
    "popularity.desc".to_string()
}

async fn get_status(State(tmdb): State<Arc<TmdbService>>) -> Json<MetadataStatusResponse> {
    Json(tmdb.get_status())
}

async fn get_movie(
    State(tmdb): State<Arc<TmdbService>>,
    Query(query): Query<MovieQuery>,
) -> Result<Json<MovieMetadata>, (StatusCode, Json<serde_json::Value>)> {
    let title = query.title.unwrap_or_default().trim().to_string();
    if title.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(json!({ "detail": "Movie title parameter 'title' is required" })),
        ));
    }

    let meta = tmdb.search_and_get_metadata(&title, query.year).await;
    Ok(Json(meta))
}

async fn get_trending(
    State(tmdb): State<Arc<TmdbService>>,
    Query(query): Query<TrendingQuery>,
) -> Json<TrendingMoviesResponse> {
    let window = if query.time_window == "day" { "day" } else { "week" };
    let page = query.page.clamp(1, 10);
    Json(tmdb.get_trending_movies(window, page).await)
}

async fn get_popular(
    State(tmdb): State<Arc<TmdbService>>,
    Query(query): Query<PageQuery>,
) -> Json<TrendingMoviesResponse> {
    let page = query.page.clamp(1, 10);
    Json(tmdb.get_popular_movies(page).await)
}

async fn get_top_rated(
    State(tmdb): State<Arc<TmdbService>>,
    Query(query): Query<PageQuery>,
) -> Json<TrendingMoviesResponse> {
    let page = query.page.clamp(1, 10);
    Json(tmdb.get_top_rated_movies(page).await)
}

async fn get_discover(
    State(tmdb): State<Arc<TmdbService>>,
    Query(query): Query<DiscoverQuery>,
) -> Json<TrendingMoviesResponse> {
    let page = query.page.clamp(1, 10);
    Json(tmdb.discover_movies(&query.language, &query.sort_by, page).await)
}

pub fn create_metadata_router(tmdb: Arc<TmdbService>) -> Router {
    Router::new()
        .route("/status", get(get_status))
        .route("/movie", get(get_movie))
        .route("/trending", get(get_trending))
        .route("/popular", get(get_popular))
        .route("/top-rated", get(get_top_rated))
        .route("/discover", get(get_discover))
        .with_state(tmdb)
}
