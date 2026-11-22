use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::RwLock;
use serde_json::Value;

use crate::models::metadata::{
    CastMember, MetadataStatusResponse, MovieMetadata, TrendingMoviesResponse,
};
use crate::services::sanitize::sanitize_movie_query;

const TMDB_BASE_URL: &str = "https://api.themoviedb.org/3";
const TMDB_IMAGE_BASE_URL: &str = "https://image.tmdb.org/t/p";
const METADATA_CACHE_TTL_SECS: u64 = 86400; // 24 hours
const FALLBACK_CACHE_TTL_SECS: u64 = 60;    // 1 minute
const TRENDING_CACHE_TTL_SECS: u64 = 3600;  // 1 hour

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn get_today_iso() -> String {
    let secs = now_secs();
    let days = (secs / 86400) as i64;
    let z = days + 719468;
    let era = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1024 + doe / 1461 - doe / 14245) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}", y, m, d)
}

fn format_image_url(path: Option<&str>, size: &str) -> Option<String> {
    path.map(|p| {
        let clean = p.trim_start_matches('/');
        format!("{}/{}/{}", TMDB_IMAGE_BASE_URL, size, clean)
    })
}

#[derive(Debug, Clone)]
pub struct TmdbConfig {
    pub proxy_url: Option<String>,
    pub supabase_anon_key: Option<String>,
    pub direct_tmdb_key: Option<String>,
}

impl Default for TmdbConfig {
    fn default() -> Self {
        // Safe configuration: read from environment variables if set by user/developer,
        // but no hardcoded secret keys in code.
        let proxy_url = std::env::var("CINEFORGE_TMDB_PROXY_URL")
            .ok()
            .or_else(|| {
                // Only use Supabase URL for proxy if explicitly enabled via flag
                // or when no direct TMDB key is provided
                let use_supabase_proxy = std::env::var("CINEFORGE_USE_SUPABASE_TMDB_PROXY")
                    .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
                    .unwrap_or(false);
                if use_supabase_proxy {
                    std::env::var("VITE_SUPABASE_URL")
                        .ok()
                        .or_else(|| std::env::var("SUPABASE_URL").ok())
                        .map(|u| format!("{}/functions/v1/tmdb-proxy", u.trim_end_matches('/')))
                } else {
                    None
                }
            });

        let supabase_anon_key = std::env::var("VITE_SUPABASE_ANON_KEY")
            .ok()
            .or_else(|| std::env::var("SUPABASE_ANON_KEY").ok());

        let direct_tmdb_key = std::env::var("TMDB_API_KEY").ok();

        Self {
            proxy_url,
            supabase_anon_key,
            direct_tmdb_key,
        }
    }
}

pub struct TmdbService {
    config: TmdbConfig,
    client: reqwest::Client,
    movie_cache: Arc<RwLock<HashMap<String, (u64, MovieMetadata)>>>,
    trending_cache: Arc<RwLock<HashMap<String, (u64, TrendingMoviesResponse)>>>,
}

impl TmdbService {
    pub fn new(config: TmdbConfig) -> Self {
        let mut builder = reqwest::Client::builder()
            .timeout(Duration::from_secs(6));

        // Resilient DNS resolution for api.themoviedb.org:
        // Regional ISPs (such as Reliance Jio in India) hijack or sinkhole DNS queries for
        // `api.themoviedb.org` to ISP block IPs (e.g. 49.44.79.236), which drop port 443 packets
        // and cause desktop metadata requests to hang and time out.
        // We configure resolve overrides targeting authentic AWS CloudFront anycast IPs.
        let cf_addrs = [
            std::net::SocketAddr::from(([3, 175, 86, 67], 443)),
            std::net::SocketAddr::from(([3, 175, 86, 103], 443)),
            std::net::SocketAddr::from(([3, 175, 86, 50], 443)),
        ];
        for addr in cf_addrs {
            builder = builder.resolve("api.themoviedb.org", addr);
        }

        let client = builder.build().unwrap_or_default();

        Self {
            config,
            client,
            movie_cache: Arc::new(RwLock::new(HashMap::new())),
            trending_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn is_configured(&self) -> bool {
        if let Some(ref direct_key) = self.config.direct_tmdb_key {
            if !direct_key.trim().is_empty() {
                return true;
            }
        }
        if let Some(ref proxy_url) = self.config.proxy_url {
            if !proxy_url.trim().is_empty() {
                return true;
            }
        }
        false
    }

    pub fn get_status(&self) -> MetadataStatusResponse {
        let configured = self.is_configured();
        MetadataStatusResponse {
            status: if configured { "ready".to_string() } else { "unconfigured".to_string() },
            configured,
        }
    }

    pub fn create_fallback_metadata(&self, raw_title: &str, year: Option<i32>) -> MovieMetadata {
        let (clean_title, parsed_year) = sanitize_movie_query(raw_title);
        let effective_year = year.or(parsed_year);
        MovieMetadata {
            tmdb_id: None,
            imdb_id: None,
            title: clean_title.clone(),
            original_title: Some(clean_title.clone()),
            overview: Some(format!(
                "Stream {} in high definition via Cineforge streaming pipeline.",
                clean_title
            )),
            release_date: None,
            year: effective_year.map(|y| y.to_string()),
            rating: None,
            vote_count: None,
            runtime: None,
            genres: vec![],
            poster_url: None,
            backdrop_url: None,
            trailer_key: None,
            directors: vec![],
            cast: vec![],
            source: "fallback".to_string(),
        }
    }

    async fn fetch_upstream_json(&self, endpoint: &str, query_params: Vec<(&str, String)>) -> Option<Value> {
        // 1. Try Supabase Edge Function proxy if configured
        if let Some(ref proxy_url) = self.config.proxy_url {
            if let Ok(mut url) = reqwest::Url::parse(proxy_url) {
                url.query_pairs_mut().append_pair("endpoint", endpoint);
                for (k, v) in &query_params {
                    url.query_pairs_mut().append_pair(k, v);
                }

                let mut req_builder = self.client.get(url).header("Accept", "application/json");

                if let Some(ref anon_key) = self.config.supabase_anon_key {
                    req_builder = req_builder
                        .header("apikey", anon_key)
                        .header("Authorization", format!("Bearer {}", anon_key));
                }

                if let Ok(resp) = req_builder.send().await {
                    if resp.status().is_success() {
                        if let Ok(json) = resp.json::<Value>().await {
                            return Some(json);
                        }
                    } else {
                        log::debug!("TMDb proxy responded with status: {}", resp.status());
                    }
                }
            }
        }

        // 2. Fall back to direct TMDb call if configured
        if let Some(ref key) = self.config.direct_tmdb_key {
            let full_url = format!("{}{}", TMDB_BASE_URL, endpoint);
            if let Ok(url) = reqwest::Url::parse(&full_url) {
                let mut req = self.client.get(url).header("Accept", "application/json");
                let mut direct_params = query_params.clone();

                if key.starts_with("eyJ") {
                    req = req.header("Authorization", format!("Bearer {}", key));
                } else {
                    direct_params.push(("api_key", key.clone()));
                }

                if let Some(build_req) = req.try_clone() {
                    if let Ok(built) = build_req.build() {
                        let mut final_url = built.url().clone();
                        for (k, v) in direct_params {
                            final_url.query_pairs_mut().append_pair(k, &v);
                        }
                        if let Ok(resp) = self.client.get(final_url).header("Accept", "application/json").send().await {
                            if resp.status().is_success() {
                                return resp.json::<Value>().await.ok();
                            } else {
                                log::debug!("Direct TMDb call returned HTTP status: {}", resp.status());
                            }
                        }
                    }
                }
            }
        }

        None
    }

    pub async fn search_and_get_metadata(&self, title: &str, year: Option<i32>) -> MovieMetadata {
        let (clean_title, parsed_year) = sanitize_movie_query(title);
        let effective_year = year.or(parsed_year);
        let cache_key = format!("{}:{}", clean_title.to_lowercase(), effective_year.unwrap_or(0));
        let now = now_secs();

        // 1. Check in-memory cache
        {
            let cache = self.movie_cache.read().await;
            if let Some((timestamp, meta)) = cache.get(&cache_key) {
                let ttl = if meta.source == "fallback" {
                    FALLBACK_CACHE_TTL_SECS
                } else {
                    METADATA_CACHE_TTL_SECS
                };
                if now - timestamp < ttl {
                    return meta.clone();
                }
            }
        }

        // 2. Fallback if not configured
        if !self.is_configured() {
            let fallback = self.create_fallback_metadata(&clean_title, effective_year);
            let mut cache = self.movie_cache.write().await;
            cache.insert(cache_key, (now, fallback.clone()));
            return fallback;
        }

        // 3. Search TMDb
        let mut params = vec![
            ("query", clean_title.clone()),
            ("include_adult", "false".to_string()),
        ];
        if let Some(y) = effective_year {
            params.push(("year", y.to_string()));
        }

        let mut data = self.fetch_upstream_json("/search/movie", params.clone()).await;
        let mut results = data
            .as_ref()
            .and_then(|d| d.get("results"))
            .and_then(|r| r.as_array())
            .cloned()
            .unwrap_or_default();

        // Retry without year if zero results
        if results.is_empty() && effective_year.is_some() {
            let retry_params = vec![
                ("query", clean_title.clone()),
                ("include_adult", "false".to_string()),
            ];
            data = self.fetch_upstream_json("/search/movie", retry_params).await;
            results = data
                .as_ref()
                .and_then(|d| d.get("results"))
                .and_then(|r| r.as_array())
                .cloned()
                .unwrap_or_default();
        }

        // TV fallback if still zero results
        if results.is_empty() {
            let tv_params = vec![
                ("query", clean_title.clone()),
                ("include_adult", "false".to_string()),
            ];
            if let Some(tv_data) = self.fetch_upstream_json("/search/tv", tv_params).await {
                if let Some(tv_results) = tv_data.get("results").and_then(|r| r.as_array()) {
                    if let Some(top_tv) = tv_results.first() {
                        let first_air = top_tv.get("first_air_date").and_then(|d| d.as_str()).unwrap_or("");
                        let tv_year = if first_air.len() >= 4 {
                            Some(first_air[..4].to_string())
                        } else {
                            effective_year.map(|y| y.to_string())
                        };

                        let poster_p = top_tv.get("poster_path").and_then(|p| p.as_str());
                        let backdrop_p = top_tv.get("backdrop_path").and_then(|p| p.as_str());
                        let title_str = top_tv.get("name").and_then(|n| n.as_str()).unwrap_or(&clean_title).to_string();

                        let tv_meta = MovieMetadata {
                            tmdb_id: top_tv.get("id").and_then(|id| id.as_i64()),
                            imdb_id: None,
                            title: title_str.clone(),
                            original_title: top_tv.get("original_name").and_then(|n| n.as_str()).map(|s| s.to_string()),
                            overview: top_tv.get("overview").and_then(|o| o.as_str()).map(|s| s.to_string()),
                            release_date: Some(first_air.to_string()),
                            year: tv_year,
                            rating: top_tv.get("vote_average").and_then(|v| v.as_f64()).map(|r| (r * 10.0).round() / 10.0),
                            vote_count: top_tv.get("vote_count").and_then(|v| v.as_i64()),
                            runtime: None,
                            genres: vec![],
                            poster_url: format_image_url(poster_p, "w500"),
                            backdrop_url: format_image_url(backdrop_p, "w1280"),
                            trailer_key: None,
                            directors: vec![],
                            cast: vec![],
                            source: "tmdb".to_string(),
                        };

                        let mut cache = self.movie_cache.write().await;
                        cache.insert(cache_key, (now, tv_meta.clone()));
                        return tv_meta;
                    }
                }
            }

            let fallback = self.create_fallback_metadata(&clean_title, effective_year);
            let mut cache = self.movie_cache.write().await;
            cache.insert(cache_key, (now, fallback.clone()));
            return fallback;
        }

        // 4. Disambiguate results using scoring function
        let score_movie = |m: &Value| -> f64 {
            let mut score = 0.0;
            let m_title = m.get("title").or_else(|| m.get("original_title")).and_then(|t| t.as_str()).unwrap_or("").to_lowercase();
            let m_date = m.get("release_date").and_then(|d| d.as_str()).unwrap_or("");
            let m_year: Option<i32> = if m_date.len() >= 4 { m_date[..4].parse().ok() } else { None };
            let vote_cnt = m.get("vote_count").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let pop = m.get("popularity").and_then(|p| p.as_f64()).unwrap_or(0.0);

            if m_title == clean_title.to_lowercase() {
                score += 5000.0;
            } else if m_title.contains(&clean_title.to_lowercase()) {
                score += 1000.0;
            }

            if let (Some(eff_y), Some(my)) = (effective_year, m_year) {
                if eff_y == my {
                    score += 10000.0;
                } else if (eff_y - my).abs() <= 1 {
                    score += 500.0;
                }
            }

            score += vote_cnt.min(50000.0) * 1.5;
            score += pop * 2.0;
            score
        };

        let mut scored_results = results;
        scored_results.sort_by(|a, b| {
            score_movie(b).partial_cmp(&score_movie(a)).unwrap_or(std::cmp::Ordering::Equal)
        });

        let top_movie = &scored_results[0];
        let movie_id = match top_movie.get("id").and_then(|id| id.as_i64()) {
            Some(id) => id,
            None => {
                let fallback = self.create_fallback_metadata(&clean_title, effective_year);
                let mut cache = self.movie_cache.write().await;
                cache.insert(cache_key, (now, fallback.clone()));
                return fallback;
            }
        };

        // 5. Fetch full details with credits & videos
        let details_endpoint = format!("/movie/{}", movie_id);
        let details_params = vec![("append_to_response", "credits,videos".to_string())];
        let details_data = self.fetch_upstream_json(&details_endpoint, details_params).await;

        let meta = if let Some(ref ext) = details_data {
            self.parse_movie_dict(ext, Some(ext))
        } else {
            self.parse_movie_dict(top_movie, None)
        };

        let mut cache = self.movie_cache.write().await;
        cache.insert(cache_key, (now, meta.clone()));
        meta
    }

    fn parse_movie_dict(&self, data: &Value, extended_data: Option<&Value>) -> MovieMetadata {
        let tmdb_id = data.get("id").and_then(|id| id.as_i64());
        let imdb_id = extended_data
            .and_then(|e| e.get("imdb_id"))
            .or_else(|| data.get("imdb_id"))
            .and_then(|id| id.as_str())
            .map(|s| s.to_string());

        let title = data.get("title")
            .or_else(|| data.get("name"))
            .and_then(|t| t.as_str())
            .unwrap_or("Unknown")
            .to_string();

        let original_title = data.get("original_title").and_then(|t| t.as_str()).map(|s| s.to_string());
        let overview = data.get("overview").and_then(|o| o.as_str()).map(|s| s.to_string());
        let release_date = data.get("release_date").and_then(|d| d.as_str()).map(|s| s.to_string());
        let year = release_date.as_ref().and_then(|d| {
            if d.len() >= 4 { Some(d[..4].to_string()) } else { None }
        });

        let vote_avg = data.get("vote_average").and_then(|v| v.as_f64());
        let rating = vote_avg.filter(|v| *v > 0.0).map(|v| (v * 10.0).round() / 10.0);
        let vote_count = data.get("vote_count").and_then(|v| v.as_i64());
        let runtime = data.get("runtime").and_then(|r| r.as_i64());

        let mut genres = vec![];
        if let Some(genre_arr) = data.get("genres").and_then(|g| g.as_array()) {
            for g in genre_arr {
                if let Some(name) = g.get("name").and_then(|n| n.as_str()) {
                    genres.push(name.to_string());
                }
            }
        }

        let poster_url = format_image_url(data.get("poster_path").and_then(|p| p.as_str()), "w500");
        let backdrop_url = format_image_url(data.get("backdrop_path").and_then(|p| p.as_str()), "w1280");

        let mut directors = vec![];
        let mut cast_list = vec![];
        let mut trailer_key = None;

        if let Some(ext) = extended_data {
            if let Some(credits) = ext.get("credits") {
                if let Some(cast_arr) = credits.get("cast").and_then(|c| c.as_array()) {
                    for c in cast_arr.iter().take(10) {
                        if let Some(name) = c.get("name").and_then(|n| n.as_str()) {
                            let profile_path = c.get("profile_path").and_then(|p| p.as_str()).map(|s| s.to_string());
                            let profile_url = format_image_url(profile_path.as_deref(), "w185");
                            let character = c.get("character").and_then(|ch| ch.as_str()).unwrap_or("").to_string();
                            cast_list.push(CastMember {
                                name: name.to_string(),
                                character,
                                profile_path,
                                profile_url,
                            });
                        }
                    }
                }

                if let Some(crew_arr) = credits.get("crew").and_then(|c| c.as_array()) {
                    for cr in crew_arr {
                        if cr.get("job").and_then(|j| j.as_str()) == Some("Director") {
                            if let Some(name) = cr.get("name").and_then(|n| n.as_str()) {
                                if !directors.contains(&name.to_string()) {
                                    directors.push(name.to_string());
                                }
                            }
                        }
                    }
                }
            }

            if let Some(videos) = ext.get("videos").and_then(|v| v.get("results")).and_then(|r| r.as_array()) {
                for v in videos {
                    if v.get("site").and_then(|s| s.as_str()) == Some("YouTube") {
                        let v_type = v.get("type").and_then(|t| t.as_str()).unwrap_or("");
                        if v_type == "Trailer" || v_type == "Teaser" {
                            if let Some(key) = v.get("key").and_then(|k| k.as_str()) {
                                trailer_key = Some(key.to_string());
                                break;
                            }
                        }
                    }
                }
            }
        }

        MovieMetadata {
            tmdb_id,
            imdb_id,
            title,
            original_title,
            overview,
            release_date,
            year,
            rating,
            vote_count,
            runtime,
            genres,
            poster_url,
            backdrop_url,
            trailer_key,
            directors,
            cast: cast_list,
            source: "tmdb".to_string(),
        }
    }

    async fn fetch_movie_list(
        &self,
        endpoint: &str,
        extra_params: Vec<(&str, String)>,
        cache_key: &str,
        min_votes: i64,
    ) -> TrendingMoviesResponse {
        let now = now_secs();

        // Check cache
        {
            let cache = self.trending_cache.read().await;
            if let Some((timestamp, cached_res)) = cache.get(cache_key) {
                if now - timestamp < TRENDING_CACHE_TTL_SECS {
                    return cached_res.clone();
                }
            }
        }

        if !self.is_configured() {
            return TrendingMoviesResponse {
                page: 1,
                total_pages: 1,
                results: vec![],
            };
        }

        let ott_cutoff = get_today_iso();
        if let Some(data) = self.fetch_upstream_json(endpoint, extra_params).await {
            if let Some(raw_results) = data.get("results").and_then(|r| r.as_array()) {
                let mut parsed = vec![];
                for item in raw_results {
                    // Must have valid poster
                    if item.get("poster_path").and_then(|p| p.as_str()).is_none() {
                        continue;
                    }
                    // Must not be unreleased
                    let rel_date = item.get("release_date").and_then(|d| d.as_str()).unwrap_or("");
                    if rel_date.is_empty() || rel_date > ott_cutoff.as_str() {
                        continue;
                    }
                    // Must have sufficient vote count
                    let vote_cnt = item.get("vote_count").and_then(|v| v.as_i64()).unwrap_or(0);
                    if vote_cnt < min_votes {
                        continue;
                    }

                    parsed.push(self.parse_movie_dict(item, None));
                }

                let page = data.get("page").and_then(|p| p.as_i64()).unwrap_or(1);
                let total_pages = data.get("total_pages").and_then(|p| p.as_i64()).unwrap_or(1);
                let response = TrendingMoviesResponse {
                    page,
                    total_pages,
                    results: parsed,
                };

                let mut cache = self.trending_cache.write().await;
                cache.insert(cache_key.to_string(), (now, response.clone()));
                return response;
            }
        }

        TrendingMoviesResponse {
            page: 1,
            total_pages: 1,
            results: vec![],
        }
    }

    pub async fn get_trending_movies(&self, _time_window: &str, page: i64) -> TrendingMoviesResponse {
        let cache_key = format!("ott_trending_released:{}", page);
        let now = now_secs();

        // Check cache
        {
            let cache = self.trending_cache.read().await;
            if let Some((timestamp, cached_res)) = cache.get(&cache_key) {
                if now - timestamp < TRENDING_CACHE_TTL_SECS {
                    return cached_res.clone();
                }
            }
        }

        if !self.is_configured() {
            // Return curated fallback list of released cinema matching Python backend
            let samples = [
                ("Inception", 2010),
                ("Interstellar", 2014),
                ("Dune: Part Two", 2024),
                ("The Dark Knight", 2008),
                ("Avengers: Endgame", 2019),
            ];
            let results: Vec<MovieMetadata> = samples
                .iter()
                .map(|(t, y)| self.create_fallback_metadata(t, Some(*y)))
                .collect();

            let res = TrendingMoviesResponse {
                page: 1,
                total_pages: 1,
                results,
            };
            return res;
        }

        let ott_cutoff = get_today_iso();
        let params = vec![
            ("sort_by", "popularity.desc".to_string()),
            ("with_release_type", "4|5|6".to_string()),
            ("primary_release_date.lte", ott_cutoff),
            ("vote_count.gte", "100".to_string()),
            ("include_adult", "false".to_string()),
            ("page", page.to_string()),
        ];

        self.fetch_movie_list("/discover/movie", params, &cache_key, 100).await
    }

    pub async fn get_popular_movies(&self, page: i64) -> TrendingMoviesResponse {
        let ott_cutoff = get_today_iso();
        let params = vec![
            ("sort_by", "popularity.desc".to_string()),
            ("with_release_type", "4|5|6".to_string()),
            ("primary_release_date.lte", ott_cutoff),
            ("vote_count.gte", "150".to_string()),
            ("include_adult", "false".to_string()),
            ("page", page.to_string()),
        ];
        let cache_key = format!("popular_ott_released:{}", page);
        self.fetch_movie_list("/discover/movie", params, &cache_key, 150).await
    }

    pub async fn get_top_rated_movies(&self, page: i64) -> TrendingMoviesResponse {
        let ott_cutoff = get_today_iso();
        let params = vec![
            ("sort_by", "vote_average.desc".to_string()),
            ("with_release_type", "4|5|6".to_string()),
            ("vote_count.gte", "500".to_string()),
            ("primary_release_date.lte", ott_cutoff),
            ("include_adult", "false".to_string()),
            ("page", page.to_string()),
        ];
        let cache_key = format!("top_rated_masterpieces:{}", page);
        self.fetch_movie_list("/discover/movie", params, &cache_key, 1000).await
    }

    pub async fn discover_movies(&self, language: &str, sort_by: &str, page: i64) -> TrendingMoviesResponse {
        let ott_cutoff = get_today_iso();
        let params = vec![
            ("with_original_language", language.to_string()),
            ("sort_by", sort_by.to_string()),
            ("with_release_type", "4|5|6".to_string()),
            ("primary_release_date.lte", ott_cutoff),
            ("vote_count.gte", "25".to_string()),
            ("include_adult", "false".to_string()),
            ("page", page.to_string()),
        ];
        let cache_key = format!("discover_released:{}:{}", language, page);
        self.fetch_movie_list("/discover/movie", params, &cache_key, 25).await
    }
}
