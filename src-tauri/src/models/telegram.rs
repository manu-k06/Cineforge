use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct TelegramUserInfo {
    pub id: i64,
    pub first_name: String,
    pub last_name: Option<String>,
    pub username: Option<String>,
    pub phone: Option<String>,
    pub is_premium: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TelegramAuthStatusResponse {
    pub connected: bool,
    pub status: String, // "disconnected", "qr_pending", "code_pending", "password_pending", "connected"
    pub user: Option<TelegramUserInfo>,
    #[serde(default)]
    pub personal_bot: Option<crate::models::provisioning::PersonalBotInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TelegramQrResponse {
    pub qr_uri: String,
    pub qr_svg: String,
    pub expires_in: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PhoneLoginRequest {
    pub phone: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CodeLoginRequest {
    pub code: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PasswordLoginRequest {
    pub password: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TelegramAuthActionResponse {
    pub status: String,
    pub message: String,
    pub user: Option<TelegramUserInfo>,
    pub hint: Option<String>,
}
