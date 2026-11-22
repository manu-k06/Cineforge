use serde::{Deserialize, Serialize};

/// Durable account-to-bot mapping preserved across sessions and restarts.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PersonalBotMapping {
    pub user_id: i64,
    pub bot_id: i64,
    pub bot_username: String,
    pub bot_access_hash: i64,
    pub created_at: i64,
}

/// Non-sensitive summary of the user's personal streamer bot exposed to UI.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PersonalBotInfo {
    pub bot_id: i64,
    pub bot_username: String,
    pub status: String, // "ready", "provisioning", "error"
}

/// Request to initiate a short-lived account ownership challenge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeRequest {
    pub user_id: i64,
}

/// Response containing the single-use challenge nonce and manager bot details.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeResponse {
    pub challenge_nonce: String,
    pub manager_bot_username: String,
    pub has_existing_bot: bool,
    pub existing_bot_username: Option<String>,
}

/// Request to register a freshly created managed bot in the durable provisioner store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterBotRequest {
    pub challenge_nonce: String,
    pub bot_id: i64,
    pub bot_access_hash: i64,
    pub bot_username: String,
}

/// Request to export the personal streamer bot token for a verified challenge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenRequest {
    pub challenge_nonce: String,
}

/// Secure response returning the personal streamer bot token to the verified owner.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenResponse {
    pub bot_token: String,
    pub bot_id: i64,
    pub bot_username: String,
}
