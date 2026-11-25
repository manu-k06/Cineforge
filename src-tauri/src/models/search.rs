use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::models::metadata::MovieMetadata;

/// Channel membership or access requirement imposed by the bot or Telegram.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct ChannelRequirement {
    pub required: bool,
    pub channel_title: Option<String>,
    pub channel_username: Option<String>,
    pub invite_url: Option<String>,
    #[serde(default)]
    pub channel_urls: Vec<String>,
    pub message: String,
    pub retry_callback: Option<String>,
    pub retry_start_payload: Option<String>,
}

impl ChannelRequirement {
    /// Returns all unique channel URLs extracted from the gate message.
    pub fn all_channel_urls(&self) -> Vec<String> {
        if !self.channel_urls.is_empty() {
            return self.channel_urls.clone();
        }
        if let Some(ref url) = self.invite_url {
            return vec![url.clone()];
        }
        if let Some(ref u) = self.channel_username {
            return vec![format!("https://t.me/{}", u.trim_start_matches('@'))];
        }
        Vec::new()
    }
}

impl std::fmt::Display for ChannelRequirement {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if let Some(ref title) = self.channel_title {
            write!(f, "{}: {}", title, self.message)
        } else {
            write!(f, "{}", self.message)
        }
    }
}

/// A parsed, normalized media stream candidate discovered from the Telegram bot.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchCandidate {
    pub candidate_id: String,
    pub source_bot: String,
    pub source_message_id: i64,
    pub start_payload: Option<String>,
    pub callback_data: Option<String>,
    pub display_text: String,
    pub title: String,
    pub size: Option<String>,
    pub size_bytes: Option<i64>,
    pub quality: String,
    pub language: Option<String>,
    pub extension: Option<String>,
    pub container: Option<String>,
    pub browser_playable: bool,
    pub playback_mode: String,
    pub compatibility_reason: Option<String>,
    pub page_number: i64,
}

/// Pagination information extracted from bot responses.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct SearchPaginationInfo {
    pub current_page: i64,
    pub total_pages: i64,
    pub total_results: i64,
    pub has_next: bool,
    pub has_prev: bool,
    pub next_callback_data: Option<String>,
    pub prev_callback_data: Option<String>,
    pub source_message_id: Option<i64>,
}

/// Unified response model for search requests returned to the frontend.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct SearchResponse {
    pub query: String,
    pub candidates: Vec<SearchCandidate>,
    pub title_groups: HashMap<String, Vec<SearchCandidate>>,
    pub pagination: Option<SearchPaginationInfo>,
    pub channel_requirement: Option<ChannelRequirement>,
    pub metadata_enrichment: HashMap<String, MovieMetadata>,
    pub is_cached: bool,
    pub error: Option<String>,
}

/// Request to validate and select a candidate for upcoming playback / delivery.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SelectedResultRequest {
    pub candidate_id: String,
    pub source_bot: Option<String>,
    pub source_message_id: Option<i64>,
    pub start_payload: Option<String>,
    pub callback_data: Option<String>,
    pub source_url: Option<String>,
    #[serde(rename = "type")]
    pub selection_type: Option<String>,
}

/// Response returned after resolving and validating candidate selection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SelectedResultResponse {
    pub status: String, // "resolved", "action_required", "error"
    pub resolved_type: String, // "callback", "telegram_deep_link", "url"
    pub target_bot: String,
    pub action_summary: String,
    pub details: serde_json::Value,
    pub channel_requirement: Option<ChannelRequirement>,
}

/// Search autocomplete suggestion item.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchSuggestionItem {
    pub id: i64,
    pub title: String,
    pub year: Option<String>,
    pub rating: Option<String>,
    pub poster_url: Option<String>,
    pub backdrop_url: Option<String>,
    pub media_type: String,
    pub overview: String,
}

/// Search autocomplete response model.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchSuggestionsResponse {
    pub query: String,
    pub suggestions: Vec<SearchSuggestionItem>,
}
