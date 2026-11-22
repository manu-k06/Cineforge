use std::collections::HashMap;
use std::sync::{Arc, Mutex, MutexGuard};
use tokio::sync::RwLock;

use grammers_client::client::{LoginToken, PasswordToken};
use grammers_client::{Client, SenderPool};
use grammers_session::types::{ChannelState, DcOption, PeerId, PeerInfo, UpdateState, UpdatesState};
use grammers_session::{BoxFuture, Session, SessionData};
use grammers_tl_types as tl;
use serde::{Deserialize, Serialize};

use crate::models::telegram::{
    TelegramAuthActionResponse, TelegramAuthStatusResponse, TelegramQrResponse, TelegramUserInfo,
};
use crate::services::storage;

/// Serialized session payload for DPAPI encryption at rest.
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct PersistedSessionData {
    pub home_dc: i32,
    pub dc_options: HashMap<i32, DcOption>,
    pub peer_infos: HashMap<PeerId, PeerInfo>,
    pub updates_state: UpdatesState,
}

impl From<&SessionData> for PersistedSessionData {
    fn from(data: &SessionData) -> Self {
        Self {
            home_dc: data.home_dc,
            dc_options: data.dc_options.clone(),
            peer_infos: data.peer_infos.clone(),
            updates_state: data.updates_state.clone(),
        }
    }
}

impl From<PersistedSessionData> for SessionData {
    fn from(data: PersistedSessionData) -> Self {
        Self {
            home_dc: data.home_dc,
            dc_options: data.dc_options,
            peer_infos: data.peer_infos,
            updates_state: data.updates_state,
        }
    }
}

#[derive(Debug)]
pub enum DpapiSessionError {
    Poisoned,
    Storage(String),
}

impl std::fmt::Display for DpapiSessionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Poisoned => write!(f, "session lock is poisoned"),
            Self::Storage(err) => write!(f, "storage error: {err}"),
        }
    }
}

impl std::error::Error for DpapiSessionError {}

/// Custom thread-safe Session storage implementation that persists genuine
/// Telegram MTProto permanent authorization keys, DC options, and updates state
/// directly via Windows DPAPI.
pub struct DpapiSession {
    data: Mutex<SessionData>,
}

impl DpapiSession {
    pub fn new(data: SessionData) -> Self {
        Self {
            data: Mutex::new(data),
        }
    }

    pub fn data(&self) -> Result<MutexGuard<'_, SessionData>, DpapiSessionError> {
        self.data.lock().map_err(|_| DpapiSessionError::Poisoned)
    }

    pub fn clone_session_data(&self) -> Result<SessionData, DpapiSessionError> {
        let guard = self.data()?;
        Ok(SessionData {
            home_dc: guard.home_dc,
            dc_options: guard.dc_options.clone(),
            peer_infos: guard.peer_infos.clone(),
            updates_state: guard.updates_state.clone(),
        })
    }

    /// Encrypts and writes the active session data to `%APPDATA%\Cineforge\telegram_session.enc`.
    pub fn save_to_dpapi(&self) -> Result<(), DpapiSessionError> {
        let session_data = self.clone_session_data()?;
        let persisted = PersistedSessionData::from(&session_data);
        let serialized = serde_json::to_vec(&persisted)
            .map_err(|e| DpapiSessionError::Storage(e.to_string()))?;
        storage::save_encrypted_session(&serialized)
            .map_err(|e| DpapiSessionError::Storage(e.to_string()))?;
        Ok(())
    }

    /// Loads and decrypts the session data from `%APPDATA%\Cineforge\telegram_session.enc`.
    pub fn load_from_dpapi() -> Result<Self, DpapiSessionError> {
        if let Ok(Some(ciphertext)) = storage::load_encrypted_session() {
            if let Ok(persisted) = serde_json::from_slice::<PersistedSessionData>(&ciphertext) {
                let session_data = SessionData::from(persisted);
                return Ok(Self::new(session_data));
            }
        }
        Ok(Self::new(SessionData::default()))
    }
}

impl Session for DpapiSession {
    type Error = DpapiSessionError;

    fn home_dc_id(&self) -> Result<i32, Self::Error> {
        Ok(self.data()?.home_dc)
    }

    fn set_home_dc_id(&self, dc_id: i32) -> BoxFuture<'_, Result<(), Self::Error>> {
        Box::pin(async move {
            self.data()?.home_dc = dc_id;
            let _ = self.save_to_dpapi();
            Ok(())
        })
    }

    fn dc_option(&self, dc_id: i32) -> Result<Option<DcOption>, Self::Error> {
        Ok(self.data()?.dc_options.get(&dc_id).cloned())
    }

    fn set_dc_option(&self, dc_option: &DcOption) -> BoxFuture<'_, Result<(), Self::Error>> {
        let dc_option = dc_option.clone();
        Box::pin(async move {
            self.data()?
                .dc_options
                .insert(dc_option.id, dc_option.clone());
            let _ = self.save_to_dpapi();
            Ok(())
        })
    }

    fn peer(&self, peer: PeerId) -> BoxFuture<'_, Result<Option<PeerInfo>, Self::Error>> {
        Box::pin(async move { Ok(self.data()?.peer_infos.get(&peer).cloned()) })
    }

    fn cache_peer(&self, peer: PeerInfo) -> BoxFuture<'_, Result<(), Self::Error>> {
        Box::pin(async move {
            self.data()?
                .peer_infos
                .entry(peer.id())
                .or_insert_with(|| peer.clone())
                .extend_info(&peer);
            let _ = self.save_to_dpapi();
            Ok(())
        })
    }

    fn updates_state(&self) -> BoxFuture<'_, Result<UpdatesState, Self::Error>> {
        Box::pin(async move { Ok(self.data()?.updates_state.clone()) })
    }

    fn set_update_state(&self, update: UpdateState) -> BoxFuture<'_, Result<(), Self::Error>> {
        Box::pin(async move {
            let mut data = self.data()?;
            match update {
                UpdateState::All(updates_state) => {
                    data.updates_state = updates_state;
                }
                UpdateState::Primary { pts, date, seq } => {
                    data.updates_state.pts = pts;
                    data.updates_state.date = date;
                    data.updates_state.seq = seq;
                }
                UpdateState::Secondary { qts } => {
                    data.updates_state.qts = qts;
                }
                UpdateState::Channel { id, pts } => {
                    data.updates_state.channels.retain(|c| c.id != id);
                    data.updates_state.channels.push(ChannelState { id, pts });
                }
            }
            drop(data);
            let _ = self.save_to_dpapi();
            Ok(())
        })
    }
}

/// Renders a given Telegram login URI (`tg://login?token=...`) into an inline SVG string.
pub fn render_qr_svg(uri: &str) -> Result<String, String> {
    use qrcode::render::svg;
    use qrcode::QrCode;

    let code = QrCode::new(uri.as_bytes()).map_err(|e| format!("Failed to generate QR: {e}"))?;
    let image = code
        .render::<svg::Color>()
        .min_dimensions(256, 256)
        .dark_color(svg::Color("#0c0e14"))
        .light_color(svg::Color("#ffffff"))
        .build();
    Ok(image)
}

/// Strongly-typed credentials for Telegram MTProto client.
/// Loaded strictly from supported configuration without hardcoded fallbacks.
#[derive(Clone, Debug)]
pub struct TelegramAuthConfig {
    pub api_id: i32,
    pub api_hash: String,
}

impl TelegramAuthConfig {
    /// Loads Telegram API credentials from environment or loaded .env configuration.
    /// Never returns hardcoded fallback keys.
    pub fn from_env() -> Result<Self, String> {
        let api_id_raw = std::env::var("TELEGRAM_API_ID")
            .or_else(|_| std::env::var("CINEFORGE_TELEGRAM_API_ID"))
            .map_err(|_| {
                "Telegram API credentials are not configured. Please define TELEGRAM_API_ID and TELEGRAM_API_HASH in your Cineforge environment or .env file."
                    .to_string()
            })?;

        let api_id = api_id_raw.trim().parse::<i32>().map_err(|_| {
            "Invalid TELEGRAM_API_ID format: expected a valid integer."
                .to_string()
        })?;

        let api_hash = std::env::var("TELEGRAM_API_HASH")
            .or_else(|_| std::env::var("CINEFORGE_TELEGRAM_API_HASH"))
            .map_err(|_| {
                "Telegram API Hash is missing. Please define TELEGRAM_API_HASH in your Cineforge environment or .env file."
                    .to_string()
            })?
            .trim()
            .to_string();

        if api_hash.is_empty() {
            return Err("Telegram API Hash cannot be empty.".to_string());
        }

        Ok(Self { api_id, api_hash })
    }
}

/// State tracking for ongoing authorization.
pub enum MtprotoAuthState {
    Disconnected,
    QrPending {
        dc_id: i32,
        token: Vec<u8>,
        expires_at: std::time::Instant,
        qr_uri: String,
        qr_svg: String,
    },
    CodePending {
        login_token: LoginToken,
    },
    PasswordPending {
        password_token: PasswordToken,
        hint: Option<String>,
    },
    Connected {
        user: TelegramUserInfo,
    },
}

pub struct MtprotoTelegramBackend {
    config_result: Result<TelegramAuthConfig, String>,
    client: Arc<RwLock<Option<Client>>>,
    session: Arc<DpapiSession>,
    auth_state: Arc<RwLock<MtprotoAuthState>>,
    runner_task: Arc<RwLock<Option<tokio::task::JoinHandle<()>>>>,
}

fn get_cached_personal_bot() -> Option<crate::models::provisioning::PersonalBotInfo> {
    storage::load_encrypted_bot_mapping()
        .ok()
        .flatten()
        .and_then(|bytes| serde_json::from_slice::<crate::models::provisioning::PersonalBotMapping>(&bytes).ok())
        .map(|m| crate::models::provisioning::PersonalBotInfo {
            bot_id: m.bot_id,
            bot_username: m.bot_username,
            status: "ready".to_string(),
        })
}

impl MtprotoTelegramBackend {
    pub fn new(config_result: Result<TelegramAuthConfig, String>) -> Self {
        let session = Arc::new(DpapiSession::load_from_dpapi().unwrap_or_else(|_| DpapiSession::new(SessionData::default())));
        Self {
            config_result,
            client: Arc::new(RwLock::new(None)),
            session,
            auth_state: Arc::new(RwLock::new(MtprotoAuthState::Disconnected)),
            runner_task: Arc::new(RwLock::new(None)),
        }
    }

    /// Initializes client connection to Telegram MTProto servers and drives the runner task.
    async fn get_or_create_client(&self) -> Result<Client, String> {
        let config = self.config_result.as_ref().map_err(|e| e.clone())?;

        let mut client_lock = self.client.write().await;
        if let Some(ref client) = *client_lock {
            return Ok(client.clone());
        }

        // Initialize SenderPool with DpapiSession to capture and persist auth keys
        let pool = SenderPool::new(Arc::clone(&self.session), config.api_id);
        let handle = pool.handle;
        let runner = pool.runner;

        // Drive I/O in a background Tokio task so SenderPoolRunner is never dropped
        let runner_handle = tokio::spawn(async move {
            runner.run().await;
        });

        {
            let mut runner_task_lock = self.runner_task.write().await;
            *runner_task_lock = Some(runner_handle);
        }

        let client = Client::new(handle);
        *client_lock = Some(client.clone());
        Ok(client)
    }

    /// Returns the active client or initializes a new connection.
    pub async fn get_client(&self) -> Result<Client, String> {
        self.get_or_create_client().await
    }

    pub async fn get_status(&self) -> Result<TelegramAuthStatusResponse, String> {
        let state = self.auth_state.read().await;
        match &*state {
            MtprotoAuthState::Connected { user } => Ok(TelegramAuthStatusResponse {
                connected: true,
                status: "connected".to_string(),
                user: Some(user.clone()),
                personal_bot: get_cached_personal_bot(),
            }),
            MtprotoAuthState::QrPending { .. } => Ok(TelegramAuthStatusResponse {
                connected: false,
                status: "qr_pending".to_string(),
                user: None,
                personal_bot: None,
            }),
            MtprotoAuthState::CodePending { .. } => Ok(TelegramAuthStatusResponse {
                connected: false,
                status: "code_pending".to_string(),
                user: None,
                personal_bot: None,
            }),
            MtprotoAuthState::PasswordPending { .. } => Ok(TelegramAuthStatusResponse {
                connected: false,
                status: "password_pending".to_string(),
                user: None,
                personal_bot: None,
            }),
            MtprotoAuthState::Disconnected => {
                if storage::has_session() && self.config_result.is_ok() {
                    drop(state);
                    if let Ok(client) = self.get_or_create_client().await {
                        if let Ok(true) = client.is_authorized().await {
                            if let Ok(me) = client.get_me().await {
                                let user_info = TelegramUserInfo {
                                    id: me.id().bare_id().unwrap_or(0),
                                    first_name: me.first_name().unwrap_or("User").to_string(),
                                    last_name: me.last_name().map(|s| s.to_string()),
                                    username: me.username().map(|s| s.to_string()),
                                    phone: me.phone().map(|s| s.to_string()),
                                    is_premium: false,
                                };
                                let mut state_write = self.auth_state.write().await;
                                *state_write = MtprotoAuthState::Connected {
                                    user: user_info.clone(),
                                };
                                return Ok(TelegramAuthStatusResponse {
                                    connected: true,
                                    status: "connected".to_string(),
                                    user: Some(user_info),
                                    personal_bot: get_cached_personal_bot(),
                                });
                            }
                        }
                    }
                }

                Ok(TelegramAuthStatusResponse {
                    connected: false,
                    status: "disconnected".to_string(),
                    user: None,
                    personal_bot: None,
                })
            }
        }
    }

    pub async fn start_qr(&self) -> Result<TelegramQrResponse, String> {
        let config = self.config_result.as_ref().map_err(|e| e.clone())?;
        let client = self.get_or_create_client().await?;

        let mut current_dc = self.session.home_dc_id().unwrap_or(2);
        let mut attempts = 0;

        loop {
            let request = tl::functions::auth::ExportLoginToken {
                api_id: config.api_id,
                api_hash: config.api_hash.clone(),
                except_ids: Vec::new(),
            };

            let response = client
                .invoke_in_dc(current_dc, &request)
                .await
                .map_err(|e| format!("Failed to export login token from Telegram (DC {current_dc}): {e}"))?;

            match response {
                tl::enums::auth::LoginToken::Token(token) => {
                    let token_b64 = base64::Engine::encode(
                        &base64::engine::general_purpose::URL_SAFE_NO_PAD,
                        &token.token,
                    );
                    let qr_uri = format!("tg://login?token={token_b64}");
                    let qr_svg = render_qr_svg(&qr_uri)?;

                    let mut state_write = self.auth_state.write().await;
                    *state_write = MtprotoAuthState::QrPending {
                        dc_id: current_dc,
                        token: token.token,
                        expires_at: std::time::Instant::now()
                            + std::time::Duration::from_secs(token.expires as u64),
                        qr_uri: qr_uri.clone(),
                        qr_svg: qr_svg.clone(),
                    };

                    return Ok(TelegramQrResponse {
                        qr_uri,
                        qr_svg,
                        expires_in: token.expires,
                    });
                }
                tl::enums::auth::LoginToken::MigrateTo(migrate) => {
                    attempts += 1;
                    if attempts > 3 {
                        return Err(format!("Exceeded maximum DC migration attempts during QR export (target DC: {})", migrate.dc_id));
                    }
                    log::info!("Telegram QR login requested DC migration to DC {}", migrate.dc_id);
                    current_dc = migrate.dc_id;
                    let _ = self.session.set_home_dc_id(migrate.dc_id).await;
                }
                tl::enums::auth::LoginToken::Success(_) => {
                    return Err("Unexpected immediate success on QR export".to_string());
                }
            }
        }
    }

    pub async fn check_qr(&self) -> Result<TelegramAuthActionResponse, String> {
        let config = self.config_result.as_ref().map_err(|e| e.clone())?;
        let state = self.auth_state.read().await;
        let (dc_id, _token, expires_at) = match &*state {
            MtprotoAuthState::QrPending {
                dc_id,
                token,
                expires_at,
                ..
            } => (*dc_id, token.clone(), *expires_at),
            MtprotoAuthState::Connected { user } => {
                return Ok(TelegramAuthActionResponse {
                    status: "connected".to_string(),
                    message: "Already connected".to_string(),
                    user: Some(user.clone()),
                    hint: None,
                });
            }
            _ => {
                return Err("No QR login in progress. Please start a new QR code.".to_string());
            }
        };
        drop(state);

        if std::time::Instant::now() > expires_at {
            let mut state_write = self.auth_state.write().await;
            *state_write = MtprotoAuthState::Disconnected;
            return Ok(TelegramAuthActionResponse {
                status: "expired".to_string(),
                message: "QR code has expired. Please refresh the code.".to_string(),
                user: None,
                hint: None,
            });
        }

        let client = self.get_or_create_client().await?;
        let request = tl::functions::auth::ExportLoginToken {
            api_id: config.api_id,
            api_hash: config.api_hash.clone(),
            except_ids: Vec::new(),
        };

        let response = client
            .invoke_in_dc(dc_id, &request)
            .await
            .map_err(|e| format!("Failed to poll QR status: {e}"))?;

        match response {
            tl::enums::auth::LoginToken::Success(auth_success) => {
                if let tl::enums::auth::Authorization::Authorization(auth) = auth_success.authorization
                {
                    if let tl::enums::User::User(u) = auth.user {
                        let user_info = TelegramUserInfo {
                            id: u.id,
                            first_name: u.first_name.unwrap_or_default(),
                            last_name: u.last_name,
                            username: u.username,
                            phone: u.phone,
                            is_premium: false,
                        };

                        let _ = self.session.save_to_dpapi();
                        let mut state_write = self.auth_state.write().await;
                        *state_write = MtprotoAuthState::Connected {
                            user: user_info.clone(),
                        };

                        return Ok(TelegramAuthActionResponse {
                            status: "connected".to_string(),
                            message: "Successfully connected via QR code!".to_string(),
                            user: Some(user_info),
                            hint: None,
                        });
                    }
                }

                Ok(TelegramAuthActionResponse {
                    status: "qr_pending".to_string(),
                    message: "Waiting for approval in Telegram mobile app...".to_string(),
                    user: None,
                    hint: None,
                })
            }
            tl::enums::auth::LoginToken::Token(_) => Ok(TelegramAuthActionResponse {
                status: "qr_pending".to_string(),
                message: "Waiting for approval in Telegram mobile app...".to_string(),
                user: None,
                hint: None,
            }),
            tl::enums::auth::LoginToken::MigrateTo(migrate) => {
                log::info!("QR scan approved with DC migration required to DC {}", migrate.dc_id);
                let import_req = tl::functions::auth::ImportLoginToken {
                    token: migrate.token.clone(),
                };
                let imported = client
                    .invoke_in_dc(migrate.dc_id, &import_req)
                    .await
                    .map_err(|e| format!("Failed to import login token into target DC {}: {e}", migrate.dc_id))?;

                match imported {
                    tl::enums::auth::LoginToken::Success(auth_success) => {
                        if let tl::enums::auth::Authorization::Authorization(auth) = auth_success.authorization {
                            if let tl::enums::User::User(u) = auth.user {
                                let user_info = TelegramUserInfo {
                                    id: u.id,
                                    first_name: u.first_name.unwrap_or_default(),
                                    last_name: u.last_name,
                                    username: u.username,
                                    phone: u.phone,
                                    is_premium: false,
                                };
                                let _ = self.session.set_home_dc_id(migrate.dc_id).await;
                                let _ = self.session.save_to_dpapi();
                                let mut state_write = self.auth_state.write().await;
                                *state_write = MtprotoAuthState::Connected {
                                    user: user_info.clone(),
                                };
                                return Ok(TelegramAuthActionResponse {
                                    status: "connected".to_string(),
                                    message: "Successfully connected via QR code across data centers!".to_string(),
                                    user: Some(user_info),
                                    hint: None,
                                });
                            }
                        }
                        Ok(TelegramAuthActionResponse {
                            status: "qr_pending".to_string(),
                            message: "Waiting for approval in Telegram mobile app...".to_string(),
                            user: None,
                            hint: None,
                        })
                    }
                    tl::enums::auth::LoginToken::Token(t) => {
                        let token_b64 = base64::Engine::encode(
                            &base64::engine::general_purpose::URL_SAFE_NO_PAD,
                            &t.token,
                        );
                        let qr_uri = format!("tg://login?token={token_b64}");
                        let qr_svg = render_qr_svg(&qr_uri)?;
                        let mut state_write = self.auth_state.write().await;
                        *state_write = MtprotoAuthState::QrPending {
                            dc_id: migrate.dc_id,
                            token: t.token,
                            expires_at: std::time::Instant::now()
                                + std::time::Duration::from_secs(t.expires as u64),
                            qr_uri,
                            qr_svg,
                        };
                        Ok(TelegramAuthActionResponse {
                            status: "qr_pending".to_string(),
                            message: "QR code updated for your account data center.".to_string(),
                            user: None,
                            hint: None,
                        })
                    }
                    tl::enums::auth::LoginToken::MigrateTo(other) => {
                        Err(format!("Chained DC migration not supported: DC {}", other.dc_id))
                    }
                }
            }
        }
    }

    pub async fn request_phone_code(&self, phone: &str) -> Result<TelegramAuthActionResponse, String> {
        let config = self.config_result.as_ref().map_err(|e| e.clone())?;
        let client = self.get_or_create_client().await?;
        let clean_phone = phone.trim().to_string();

        let login_token = client
            .request_login_code(&clean_phone, &config.api_hash)
            .await
            .map_err(|e| format!("Failed to request verification code: {e}"))?;

        let mut state_write = self.auth_state.write().await;
        *state_write = MtprotoAuthState::CodePending { login_token };

        Ok(TelegramAuthActionResponse {
            status: "code_pending".to_string(),
            message: format!("Verification code sent for {clean_phone}"),
            user: None,
            hint: None,
        })
    }

    pub async fn submit_code(&self, code: &str) -> Result<TelegramAuthActionResponse, String> {
        let client = self.get_or_create_client().await?;
        let mut state_write = self.auth_state.write().await;

        let login_token = match &*state_write {
            MtprotoAuthState::CodePending { login_token } => login_token,
            _ => {
                return Err("No phone code login in progress.".to_string());
            }
        };

        match client.sign_in(login_token, code.trim()).await {
            Ok(user) => {
                let user_info = TelegramUserInfo {
                    id: user.id().bare_id().unwrap_or(0),
                    first_name: user.first_name().unwrap_or("User").to_string(),
                    last_name: user.last_name().map(|s| s.to_string()),
                    username: user.username().map(|s| s.to_string()),
                    phone: user.phone().map(|s| s.to_string()),
                    is_premium: false,
                };

                let _ = self.session.save_to_dpapi();
                *state_write = MtprotoAuthState::Connected {
                    user: user_info.clone(),
                };

                Ok(TelegramAuthActionResponse {
                    status: "connected".to_string(),
                    message: "Successfully signed in with verification code!".to_string(),
                    user: Some(user_info),
                    hint: None,
                })
            }
            Err(grammers_client::SignInError::PasswordRequired(password_token)) => {
                let hint = password_token.hint().map(|s| s.to_string());
                *state_write = MtprotoAuthState::PasswordPending {
                    password_token,
                    hint: hint.clone(),
                };

                Ok(TelegramAuthActionResponse {
                    status: "password_pending".to_string(),
                    message: "Two-step verification password is required.".to_string(),
                    user: None,
                    hint,
                })
            }
            Err(grammers_client::SignInError::InvalidCode) => Ok(TelegramAuthActionResponse {
                status: "invalid_code".to_string(),
                message: "The verification code you entered is invalid. Please try again."
                    .to_string(),
                user: None,
                hint: None,
            }),
            Err(e) => Err(format!("Sign in failed: {e}")),
        }
    }

    pub async fn submit_password(&self, password: &str) -> Result<TelegramAuthActionResponse, String> {
        let client = self.get_or_create_client().await?;
        let mut state_write = self.auth_state.write().await;

        let (password_token, hint) = match std::mem::replace(
            &mut *state_write,
            MtprotoAuthState::Disconnected,
        ) {
            MtprotoAuthState::PasswordPending {
                password_token,
                hint,
            } => (password_token, hint),
            _ => {
                return Err("No password pending. Please restart login.".to_string());
            }
        };

        match client.check_password(password_token, password.trim()).await {
            Ok(user) => {
                let user_info = TelegramUserInfo {
                    id: user.id().bare_id().unwrap_or(0),
                    first_name: user.first_name().unwrap_or("User").to_string(),
                    last_name: user.last_name().map(|s| s.to_string()),
                    username: user.username().map(|s| s.to_string()),
                    phone: user.phone().map(|s| s.to_string()),
                    is_premium: false,
                };

                let _ = self.session.save_to_dpapi();
                *state_write = MtprotoAuthState::Connected {
                    user: user_info.clone(),
                };

                Ok(TelegramAuthActionResponse {
                    status: "connected".to_string(),
                    message: "Two-step verification successful! Connected to Telegram.".to_string(),
                    user: Some(user_info),
                    hint: None,
                })
            }
            Err(grammers_client::SignInError::InvalidPassword(retry_token)) => {
                *state_write = MtprotoAuthState::PasswordPending {
                    password_token: retry_token,
                    hint: hint.clone(),
                };

                Ok(TelegramAuthActionResponse {
                    status: "invalid_password".to_string(),
                    message: "The 2FA password is incorrect. Please try again.".to_string(),
                    user: None,
                    hint,
                })
            }
            Err(e) => Err(format!("Password verification failed: {e}")),
        }
    }

    pub async fn disconnect(&self) -> Result<TelegramAuthActionResponse, String> {
        let client_opt = {
            let mut client_lock = self.client.write().await;
            client_lock.take()
        };

        if let Some(client) = client_opt {
            let _ = client.sign_out().await;
            client.disconnect();
        }

        let task_opt = {
            let mut task_lock = self.runner_task.write().await;
            task_lock.take()
        };
        if let Some(task) = task_opt {
            task.abort();
        }

        // Wipe encrypted session file from %APPDATA%\Cineforge\telegram_session.enc
        let _ = storage::delete_session();

        let mut state_write = self.auth_state.write().await;
        *state_write = MtprotoAuthState::Disconnected;

        Ok(TelegramAuthActionResponse {
            status: "disconnected".to_string(),
            message: "Disconnected from Telegram. Local session wiped.".to_string(),
            user: None,
            hint: None,
        })
    }
}

/// Simulated mock backend for fast, deterministic unit & integration tests.
pub struct MockTelegramBackend {
    pub state: Arc<RwLock<TelegramAuthStatusResponse>>,
    pub mock_hint: Option<String>,
}

impl MockTelegramBackend {
    pub fn new() -> Self {
        Self {
            state: Arc::new(RwLock::new(TelegramAuthStatusResponse {
                connected: false,
                status: "disconnected".to_string(),
                user: None,
                personal_bot: None,
            })),
            mock_hint: Some("Cineforge 2FA Hint".to_string()),
        }
    }

    pub fn new_connected(user: TelegramUserInfo) -> Self {
        Self {
            state: Arc::new(RwLock::new(TelegramAuthStatusResponse {
                connected: true,
                status: "connected".to_string(),
                user: Some(user),
                personal_bot: Some(crate::models::provisioning::PersonalBotInfo {
                    bot_id: 88888888,
                    bot_username: "cf_mock_streamer_bot".to_string(),
                    status: "ready".to_string(),
                }),
            })),
            mock_hint: None,
        }
    }

    pub async fn get_status(&self) -> Result<TelegramAuthStatusResponse, String> {
        let state = self.state.read().await;
        Ok(state.clone())
    }

    pub async fn start_qr(&self) -> Result<TelegramQrResponse, String> {
        let qr_uri = "tg://login?token=mock_test_token_abcdef123456".to_string();
        let qr_svg = render_qr_svg(&qr_uri)?;

        let mut state = self.state.write().await;
        state.status = "qr_pending".to_string();
        state.connected = false;

        Ok(TelegramQrResponse {
            qr_uri,
            qr_svg,
            expires_in: 60,
        })
    }

    pub async fn check_qr(&self) -> Result<TelegramAuthActionResponse, String> {
        let mut state = self.state.write().await;
        if state.status == "qr_pending" {
            let user = TelegramUserInfo {
                id: 99887766,
                first_name: "MockUser".to_string(),
                last_name: Some("Tester".to_string()),
                username: Some("mock_tester".to_string()),
                phone: Some("+1234567890".to_string()),
                is_premium: true,
            };
            state.connected = true;
            state.status = "connected".to_string();
            state.user = Some(user.clone());

            let dummy_session = PersistedSessionData::from(&SessionData::default());
            let json = serde_json::to_vec(&dummy_session).unwrap();
            let _ = storage::save_encrypted_session(&json);

            Ok(TelegramAuthActionResponse {
                status: "connected".to_string(),
                message: "Mock QR scan approved!".to_string(),
                user: Some(user),
                hint: None,
            })
        } else {
            Ok(TelegramAuthActionResponse {
                status: state.status.clone(),
                message: "No QR pending".to_string(),
                user: state.user.clone(),
                hint: None,
            })
        }
    }

    pub async fn request_phone_code(&self, phone: &str) -> Result<TelegramAuthActionResponse, String> {
        let mut state = self.state.write().await;
        state.status = "code_pending".to_string();
        state.connected = false;

        Ok(TelegramAuthActionResponse {
            status: "code_pending".to_string(),
            message: format!("Mock verification code sent to {phone}"),
            user: None,
            hint: None,
        })
    }

    pub async fn submit_code(&self, code: &str) -> Result<TelegramAuthActionResponse, String> {
        let mut state = self.state.write().await;
        if code == "2fa_code" {
            state.status = "password_pending".to_string();
            return Ok(TelegramAuthActionResponse {
                status: "password_pending".to_string(),
                message: "2FA password required".to_string(),
                user: None,
                hint: self.mock_hint.clone(),
            });
        }

        if code == "12345" {
            let user = TelegramUserInfo {
                id: 11223344,
                first_name: "PhoneUser".to_string(),
                last_name: None,
                username: Some("phone_user".to_string()),
                phone: Some("+1987654321".to_string()),
                is_premium: false,
            };
            state.connected = true;
            state.status = "connected".to_string();
            state.user = Some(user.clone());

            let dummy_session = PersistedSessionData::from(&SessionData::default());
            let json = serde_json::to_vec(&dummy_session).unwrap();
            let _ = storage::save_encrypted_session(&json);

            Ok(TelegramAuthActionResponse {
                status: "connected".to_string(),
                message: "Signed in successfully with phone code!".to_string(),
                user: Some(user),
                hint: None,
            })
        } else {
            Ok(TelegramAuthActionResponse {
                status: "invalid_code".to_string(),
                message: "Invalid verification code".to_string(),
                user: None,
                hint: None,
            })
        }
    }

    pub async fn submit_password(&self, password: &str) -> Result<TelegramAuthActionResponse, String> {
        let mut state = self.state.write().await;
        if password == "correct_password" {
            let user = TelegramUserInfo {
                id: 44556677,
                first_name: "2faUser".to_string(),
                last_name: None,
                username: Some("secure_user".to_string()),
                phone: Some("+1122334455".to_string()),
                is_premium: true,
            };
            state.connected = true;
            state.status = "connected".to_string();
            state.user = Some(user.clone());

            let dummy_session = PersistedSessionData::from(&SessionData::default());
            let json = serde_json::to_vec(&dummy_session).unwrap();
            let _ = storage::save_encrypted_session(&json);

            Ok(TelegramAuthActionResponse {
                status: "connected".to_string(),
                message: "2FA verified successfully!".to_string(),
                user: Some(user),
                hint: None,
            })
        } else {
            Ok(TelegramAuthActionResponse {
                status: "invalid_password".to_string(),
                message: "Incorrect 2FA password".to_string(),
                user: None,
                hint: self.mock_hint.clone(),
            })
        }
    }

    pub async fn disconnect(&self) -> Result<TelegramAuthActionResponse, String> {
        let mut state = self.state.write().await;
        state.connected = false;
        state.status = "disconnected".to_string();
        state.user = None;
        state.personal_bot = None;

        let _ = storage::delete_session();

        Ok(TelegramAuthActionResponse {
            status: "disconnected".to_string(),
            message: "Disconnected from Telegram. Local session removed.".to_string(),
            user: None,
            hint: None,
        })
    }
}

/// Enum dispatch backend avoiding async trait dyn limitations.
pub enum TelegramBackendKind {
    Mtproto(MtprotoTelegramBackend),
    Mock(MockTelegramBackend),
}

impl TelegramBackendKind {
    pub async fn get_status(&self) -> Result<TelegramAuthStatusResponse, String> {
        match self {
            Self::Mtproto(b) => b.get_status().await,
            Self::Mock(b) => b.get_status().await,
        }
    }

    pub async fn start_qr(&self) -> Result<TelegramQrResponse, String> {
        match self {
            Self::Mtproto(b) => b.start_qr().await,
            Self::Mock(b) => b.start_qr().await,
        }
    }

    pub async fn check_qr(&self) -> Result<TelegramAuthActionResponse, String> {
        match self {
            Self::Mtproto(b) => b.check_qr().await,
            Self::Mock(b) => b.check_qr().await,
        }
    }

    pub async fn request_phone_code(&self, phone: &str) -> Result<TelegramAuthActionResponse, String> {
        match self {
            Self::Mtproto(b) => b.request_phone_code(phone).await,
            Self::Mock(b) => b.request_phone_code(phone).await,
        }
    }

    pub async fn submit_code(&self, code: &str) -> Result<TelegramAuthActionResponse, String> {
        match self {
            Self::Mtproto(b) => b.submit_code(code).await,
            Self::Mock(b) => b.submit_code(code).await,
        }
    }

    pub async fn submit_password(&self, password: &str) -> Result<TelegramAuthActionResponse, String> {
        match self {
            Self::Mtproto(b) => b.submit_password(password).await,
            Self::Mock(b) => b.submit_password(password).await,
        }
    }

    pub async fn disconnect(&self) -> Result<TelegramAuthActionResponse, String> {
        match self {
            Self::Mtproto(b) => b.disconnect().await,
            Self::Mock(b) => b.disconnect().await,
        }
    }
}

/// Unified service entry point.
pub struct TelegramAuthService {
    backend: Arc<TelegramBackendKind>,
}

impl TelegramAuthService {
    pub fn new() -> Self {
        let config_result = TelegramAuthConfig::from_env();
        Self {
            backend: Arc::new(TelegramBackendKind::Mtproto(MtprotoTelegramBackend::new(config_result))),
        }
    }

    pub fn new_with_config(config_result: Result<TelegramAuthConfig, String>) -> Self {
        Self {
            backend: Arc::new(TelegramBackendKind::Mtproto(MtprotoTelegramBackend::new(config_result))),
        }
    }

    pub fn new_mock() -> Self {
        Self {
            backend: Arc::new(TelegramBackendKind::Mock(MockTelegramBackend::new())),
        }
    }

    pub fn new_mock_connected(user: TelegramUserInfo) -> Self {
        Self {
            backend: Arc::new(TelegramBackendKind::Mock(MockTelegramBackend::new_connected(user))),
        }
    }

    pub fn backend(&self) -> Arc<TelegramBackendKind> {
        Arc::clone(&self.backend)
    }

    pub async fn get_status(&self) -> Result<TelegramAuthStatusResponse, String> {
        self.backend.get_status().await
    }

    pub async fn start_qr(&self) -> Result<TelegramQrResponse, String> {
        self.backend.start_qr().await
    }

    pub async fn check_qr(&self) -> Result<TelegramAuthActionResponse, String> {
        self.backend.check_qr().await
    }

    pub async fn request_phone_code(&self, phone: &str) -> Result<TelegramAuthActionResponse, String> {
        self.backend.request_phone_code(phone).await
    }

    pub async fn submit_code(&self, code: &str) -> Result<TelegramAuthActionResponse, String> {
        self.backend.submit_code(code).await
    }

    pub async fn submit_password(&self, password: &str) -> Result<TelegramAuthActionResponse, String> {
        self.backend.submit_password(password).await
    }

    pub async fn disconnect(&self) -> Result<TelegramAuthActionResponse, String> {
        self.backend.disconnect().await
    }
}

impl Default for TelegramAuthService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dpapi_session_persistence_roundtrip() {
        let _guard = storage::TEST_STORAGE_MUTEX.lock().unwrap();
        let _ = storage::delete_session();

        let mut session_data = SessionData::default();
        session_data.home_dc = 4;
        let dc_option = DcOption {
            id: 4,
            ipv4: "149.154.167.50:443".parse().unwrap(),
            ipv6: "[2001:67c:4e8:f002::a]:443".parse().unwrap(),
            auth_key: Some([42u8; 256]),
        };
        session_data.dc_options.insert(4, dc_option);

        // Save session using DpapiSession
        let session = DpapiSession::new(session_data);
        session.save_to_dpapi().expect("save to dpapi failed");

        // Simulate app restart: load fresh from DPAPI storage
        let restored = DpapiSession::load_from_dpapi().expect("load from dpapi failed");
        let restored_data = restored.clone_session_data().expect("clone data failed");

        assert_eq!(restored_data.home_dc, 4);
        let restored_dc = restored_data.dc_options.get(&4).expect("DC 4 missing");
        assert_eq!(restored_dc.auth_key, Some([42u8; 256]));

        // Cleanup
        let _ = storage::delete_session();
    }

    #[test]
    fn test_missing_config_returns_safe_error() {
        let _guard = storage::TEST_STORAGE_MUTEX.lock().unwrap();
        // Clear environment variables
        unsafe {
            std::env::remove_var("TELEGRAM_API_ID");
            std::env::remove_var("CINEFORGE_TELEGRAM_API_ID");
            std::env::remove_var("TELEGRAM_API_HASH");
            std::env::remove_var("CINEFORGE_TELEGRAM_API_HASH");
        }

        let config_res = TelegramAuthConfig::from_env();
        assert!(config_res.is_err());
        let err = config_res.unwrap_err();
        assert!(err.contains("Telegram API credentials are not configured"));
    }

    #[test]
    fn test_persisted_session_serialization() {
        let session_data = SessionData::default();
        let persisted = PersistedSessionData::from(&session_data);
        let serialized = serde_json::to_vec(&persisted).expect("failed to serialize session");
        assert!(!serialized.is_empty());

        let deserialized: PersistedSessionData =
            serde_json::from_slice(&serialized).expect("failed to deserialize session");
        assert_eq!(deserialized.home_dc, session_data.home_dc);
    }

    #[test]
    fn test_render_qr_svg() {
        let svg = render_qr_svg("tg://login?token=test_token_12345").expect("render QR failed");
        assert!(svg.starts_with("<?xml") || svg.contains("<svg"));
        assert!(svg.contains("</svg>"));
    }

    #[tokio::test]
    async fn test_mock_backend_qr_flow() {
        let _guard = storage::TEST_STORAGE_MUTEX.lock().unwrap();
        let _ = storage::delete_session();
        let service = TelegramAuthService::new_mock();

        let initial_status = service.get_status().await.unwrap();
        assert_eq!(initial_status.connected, false);
        assert_eq!(initial_status.status, "disconnected");

        let qr = service.start_qr().await.unwrap();
        assert!(qr.qr_uri.starts_with("tg://login?token="));
        assert!(qr.qr_svg.contains("<svg"));

        let status_after_qr = service.get_status().await.unwrap();
        assert_eq!(status_after_qr.status, "qr_pending");

        let approved = service.check_qr().await.unwrap();
        assert_eq!(approved.status, "connected");
        assert!(approved.user.is_some());
        assert_eq!(approved.user.unwrap().first_name, "MockUser");

        let final_status = service.get_status().await.unwrap();
        assert_eq!(final_status.connected, true);
        assert_eq!(final_status.status, "connected");

        // Disconnect
        let disc = service.disconnect().await.unwrap();
        assert_eq!(disc.status, "disconnected");
        let after_disc = service.get_status().await.unwrap();
        assert_eq!(after_disc.connected, false);
        let _ = storage::delete_session();
    }

    #[tokio::test]
    async fn test_mock_backend_phone_and_2fa_flow() {
        let _guard = storage::TEST_STORAGE_MUTEX.lock().unwrap();
        let _ = storage::delete_session();
        let service = TelegramAuthService::new_mock();

        let code_req = service.request_phone_code("+1234567890").await.unwrap();
        assert_eq!(code_req.status, "code_pending");

        // Submit code requiring 2FA
        let code_res = service.submit_code("2fa_code").await.unwrap();
        assert_eq!(code_res.status, "password_pending");
        assert_eq!(code_res.hint, Some("Cineforge 2FA Hint".to_string()));

        // Submit invalid password
        let bad_pwd = service.submit_password("wrong_password").await.unwrap();
        assert_eq!(bad_pwd.status, "invalid_password");

        // Submit correct password
        let good_pwd = service.submit_password("correct_password").await.unwrap();
        assert_eq!(good_pwd.status, "connected");
        assert_eq!(good_pwd.user.unwrap().first_name, "2faUser");
        let _ = storage::delete_session();
    }
}
