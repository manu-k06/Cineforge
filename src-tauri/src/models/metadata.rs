use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct CastMember {
    pub name: String,
    #[serde(default)]
    pub character: String,
    #[serde(default)]
    pub profile_path: Option<String>,
    #[serde(default)]
    pub profile_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct CrewMember {
    pub name: String,
    pub job: String,
    #[serde(default)]
    pub department: Option<String>,
}

fn default_source() -> String {
    "tmdb".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MovieMetadata {
    #[serde(default)]
    pub tmdb_id: Option<i64>,
    #[serde(default)]
    pub imdb_id: Option<String>,
    pub title: String,
    #[serde(default)]
    pub original_title: Option<String>,
    #[serde(default)]
    pub overview: Option<String>,
    #[serde(default)]
    pub release_date: Option<String>,
    #[serde(default)]
    pub year: Option<String>,
    #[serde(default)]
    pub rating: Option<f64>,
    #[serde(default)]
    pub vote_count: Option<i64>,
    #[serde(default)]
    pub runtime: Option<i64>,
    #[serde(default)]
    pub genres: Vec<String>,
    #[serde(default)]
    pub poster_url: Option<String>,
    #[serde(default)]
    pub backdrop_url: Option<String>,
    #[serde(default)]
    pub trailer_key: Option<String>,
    #[serde(default)]
    pub directors: Vec<String>,
    #[serde(default)]
    pub cast: Vec<CastMember>,
    #[serde(default = "default_source")]
    pub source: String,
}

fn default_page() -> i64 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TrendingMoviesResponse {
    #[serde(default = "default_page")]
    pub page: i64,
    #[serde(default = "default_page")]
    pub total_pages: i64,
    #[serde(default)]
    pub results: Vec<MovieMetadata>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MetadataStatusResponse {
    pub status: String,
    pub configured: bool,
}
