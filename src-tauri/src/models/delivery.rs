use serde::{Deserialize, Serialize};

/// Request payload to deliver a specific candidate Telegram file.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CandidateDeliveryRequest {
    pub candidate_id: String,
    pub source_bot: Option<String>,
    pub start_payload: Option<String>,
    pub callback_data: Option<String>,
    pub source_message_id: Option<i64>,
    pub candidate_title: Option<String>,
    pub quality: Option<String>,
}

/// Response payload from candidate delivery containing stream and player URLs.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CandidateDeliveryResponse {
    pub success: bool,
    pub candidate_title: Option<String>,
    pub delivered_chat_id: String,
    pub delivered_message_id: i64,
    pub file_name: String,
    pub mime_type: String,
    pub file_size: i64,
    pub browser_playable: bool,
    pub container: String,
    pub playback_mode: String,
    pub session_id: String,
    pub stream_url: String,
    pub player_url: String,
    pub watch_url: Option<String>,
    pub download_url: Option<String>,
    pub elapsed_seconds: f64,
    pub error: Option<String>,
}

/// Status of the Go streamer sidecar process.
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(tag = "status", content = "details")]
pub enum StreamerStatus {
    Stopped,
    Starting,
    Running { port: u16, host: String, pid: u32 },
    Exited { code: Option<i32> },
    Failed { error: String },
}
