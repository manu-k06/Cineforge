use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;

use grammers_tl_types as tl;

use crate::models::provisioning::{
    ChallengeRequest, ChallengeResponse, PersonalBotInfo, PersonalBotMapping, RegisterBotRequest,
    TokenRequest, TokenResponse,
};
use crate::models::telegram::TelegramUserInfo;
use crate::services::storage;

/// Validates that the provisioning URL enforces HTTPS in production environments.
/// Insecure HTTP is permitted only for explicit loopback addresses (127.0.0.1, localhost, [::1])
/// or when CINEFORGE_DEV_MODE is explicitly enabled.
pub fn validate_provisioning_url(url: &str, is_dev_mode: bool) -> Result<(), String> {
    let url_trimmed = url.trim();
    if url_trimmed.is_empty() {
        return Err("Provisioning service URL cannot be empty".to_string());
    }

    let parsed = reqwest::Url::parse(url_trimmed)
        .map_err(|e| format!("Invalid provisioning URL format '{url_trimmed}': {e}"))?;

    let scheme = parsed.scheme();
    let host = parsed.host_str().unwrap_or("");

    let is_loopback = host == "127.0.0.1" || host == "localhost" || host == "[::1]";

    if scheme == "https" {
        return Ok(());
    }

    if scheme == "http" && (is_loopback || is_dev_mode) {
        return Ok(());
    }

    Err(format!(
        "Insecure provisioning URL rejected: '{url_trimmed}'. Provisioning service must use HTTPS in production."
    ))
}

#[derive(Clone)]
pub struct BotProvisioningService {
    client: reqwest::Client,
    provisioning_url: String,
    manager_bot_username: String,
    runtime_bot_token: Arc<RwLock<Option<String>>>,
    active_bot_info: Arc<RwLock<Option<PersonalBotInfo>>>,
    is_mock: bool,
}

impl BotProvisioningService {
    /// Creates a production provisioning service client targeting the remotely hosted HTTPS service.
    pub fn new() -> Self {
        let provisioning_url = std::env::var("PROVISIONING_SERVICE_URL")
            .unwrap_or_else(|_| "https://provision.cineforge.app".to_string());
        let manager_bot_username = std::env::var("CINEFORGE_MANAGER_BOT_USERNAME")
            .unwrap_or_else(|_| "CineforgeManagerBot".to_string());

        let is_dev_mode = std::env::var("CINEFORGE_DEV_MODE")
            .map(|v| v == "1" || v == "true")
            .unwrap_or(false);
        if let Err(err) = validate_provisioning_url(&provisioning_url, is_dev_mode) {
            log::warn!("Provisioning service URL configuration warning: {err}");
        }

        Self {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(15))
                .build()
                .unwrap_or_default(),
            provisioning_url,
            manager_bot_username,
            runtime_bot_token: Arc::new(RwLock::new(None)),
            active_bot_info: Arc::new(RwLock::new(None)),
            is_mock: false,
        }
    }

    /// Creates a mock provisioning service client for offline integration tests.
    pub fn new_mock(bot_id: i64, bot_username: &str, bot_token: &str) -> Self {
        Self {
            client: reqwest::Client::new(),
            provisioning_url: "http://127.0.0.1:8085".to_string(),
            manager_bot_username: "CineforgeManagerBot".to_string(),
            runtime_bot_token: Arc::new(RwLock::new(Some(bot_token.to_string()))),
            active_bot_info: Arc::new(RwLock::new(Some(PersonalBotInfo {
                bot_id,
                bot_username: bot_username.to_string(),
                status: "ready".to_string(),
            }))),
            is_mock: true,
        }
    }

    pub fn provisioning_url(&self) -> &str {
        &self.provisioning_url
    }

    pub fn manager_bot_username(&self) -> &str {
        &self.manager_bot_username
    }

    /// Returns non-sensitive info about the user's personal streamer bot if known.
    pub async fn get_personal_bot_info(&self) -> Option<PersonalBotInfo> {
        let in_memory = self.active_bot_info.read().await.clone();
        if in_memory.is_some() {
            return in_memory;
        }

        // Check local DPAPI cache
        if let Ok(Some(bytes)) = storage::load_encrypted_bot_mapping() {
            if let Ok(mapping) = serde_json::from_slice::<PersonalBotMapping>(&bytes) {
                return Some(PersonalBotInfo {
                    bot_id: mapping.bot_id,
                    bot_username: mapping.bot_username,
                    status: "ready".to_string(),
                });
            }
        }

        None
    }

    /// Returns the runtime bot token stored strictly in volatile memory.
    pub async fn get_runtime_token(&self) -> Option<String> {
        self.runtime_bot_token.read().await.clone()
    }

    /// Clears runtime tokens and memory state upon logout while keeping the durable bot mapping.
    pub async fn clear_runtime_tokens(&self) {
        *self.runtime_bot_token.write().await = None;
        *self.active_bot_info.write().await = None;
        log::info!("Personal streamer bot runtime token and active info cleared from memory.");
    }

    /// Ensures the personal streamer bot exists, verifies account ownership via challenge,
    /// exports its token, and stores it in runtime memory.
    pub async fn ensure_bot_provisioned(
        &self,
        user: &TelegramUserInfo,
        mtproto_client: Option<&grammers_client::Client>,
    ) -> Result<PersonalBotInfo, String> {
        if self.is_mock {
            if let Some(info) = self.active_bot_info.read().await.clone() {
                return Ok(info);
            }
            return Ok(PersonalBotInfo {
                bot_id: 99999999,
                bot_username: "cf_mock_streamer_bot".to_string(),
                status: "ready".to_string(),
            });
        }

        // 1. If runtime token is already active and matches current session, return immediately
        if let (Some(token), Some(info)) = (
            self.runtime_bot_token.read().await.clone(),
            self.active_bot_info.read().await.clone(),
        ) {
            if !token.is_empty() {
                return Ok(info);
            }
        }

        // Validate that provisioning URL uses HTTPS in production
        let is_dev_mode = std::env::var("CINEFORGE_DEV_MODE")
            .map(|v| v == "1" || v == "true")
            .unwrap_or(false);
        validate_provisioning_url(&self.provisioning_url, is_dev_mode)?;

        // 2. Request single-use challenge nonce from remote Provisioning Service
        let challenge_url = format!("{}/api/provision/challenge", self.provisioning_url);
        let challenge_resp = self
            .client
            .post(&challenge_url)
            .json(&ChallengeRequest { user_id: user.id })
            .send()
            .await
            .map_err(|e| format!("Failed to request provisioning challenge from {}: {e}", self.provisioning_url))?;

        if !challenge_resp.status().is_success() {
            let status = challenge_resp.status();
            let body = challenge_resp.text().await.unwrap_or_default();
            return Err(format!("Provisioning service rejected challenge request (HTTP {status}): {body}"));
        }

        let challenge: ChallengeResponse = challenge_resp
            .json()
            .await
            .map_err(|e| format!("Invalid challenge response from provisioning service: {e}"))?;

        // 3. Prove account ownership by sending /verify <nonce> to @CineforgeManagerBot via user's MTProto session
        let client = mtproto_client.ok_or_else(|| {
            "Active Telegram MTProto client required to complete account ownership challenge.".to_string()
        })?;

        let manager_username = if !challenge.manager_bot_username.is_empty() {
            challenge.manager_bot_username.clone()
        } else {
            self.manager_bot_username.clone()
        };

        let resolved_manager = client
            .invoke(&tl::functions::contacts::ResolveUsername {
                username: manager_username.clone(),
                referer: None,
            })
            .await
            .map_err(|e| format!("Failed to resolve manager bot @{manager_username}: {e}"))?;

        let manager_peer = match resolved_manager {
            tl::enums::contacts::ResolvedPeer::Peer(p) => match p.peer {
                tl::enums::Peer::User(u) => {
                    let access_hash = p.users.iter().find_map(|user_obj| {
                        if let tl::enums::User::User(real_u) = user_obj {
                            if real_u.id == u.user_id {
                                return real_u.access_hash;
                            }
                        }
                        None
                    }).unwrap_or(0);

                    tl::enums::InputPeer::User(tl::types::InputPeerUser {
                        user_id: u.user_id,
                        access_hash,
                    })
                }
                _ => return Err("Resolved manager peer is not a user/bot".to_string()),
            },
        };

        let manager_input_user = match manager_peer {
            tl::enums::InputPeer::User(ref u) => tl::enums::InputUser::User(tl::types::InputUser {
                user_id: u.user_id,
                access_hash: u.access_hash,
            }),
            _ => return Err("Invalid manager InputUser peer".to_string()),
        };

        // Send /verify <nonce> message to manager bot
        let verify_msg = format!("/verify {}", challenge.challenge_nonce);
        let random_id = {
            use std::time::SystemTime;
            SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos() as i64
        };

        client
            .invoke(&tl::functions::messages::SendMessage {
                no_webpage: true,
                silent: true,
                background: true,
                clear_draft: true,
                noforwards: true,
                update_stickersets_order: false,
                invert_media: false,
                allow_paid_floodskip: false,
                peer: manager_peer.clone(),
                reply_to: None,
                message: verify_msg,
                random_id,
                reply_markup: None,
                entities: None,
                schedule_date: None,
                schedule_repeat_period: None,
                send_as: None,
                quick_reply_shortcut: None,
                effect: None,
                allow_paid_stars: None,
                suggested_post: None,
                rich_message: None,
            })
            .await
            .map_err(|e| format!("Failed to transmit verification challenge to @{manager_username}: {e}"))?;

        // Give the remote manager bot a moment to ingest the incoming update
        tokio::time::sleep(Duration::from_millis(800)).await;

        // 4. Create managed bot if account does not have one registered yet
        let local_mapping = storage::load_encrypted_bot_mapping()
            .ok()
            .flatten()
            .and_then(|bytes| serde_json::from_slice::<PersonalBotMapping>(&bytes).ok())
            .filter(|m| m.user_id == user.id);

        if !challenge.has_existing_bot && local_mapping.is_none() {
            // Generate unique bot username: cf_<user_id>_<random_suffix>_bot
            let random_suffix = {
                use std::time::SystemTime;
                let nanos = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos();
                format!("{:x}", nanos % 0xFFFFFF)
            };
            let candidate_username = format!("cf_{}_{}_bot", user.id, random_suffix);

            // Check availability
            let _ = client.invoke(&tl::functions::bots::CheckUsername {
                additional: false,
                username: candidate_username.clone(),
            }).await;

            // Invoke MTProto bots.createBot
            let bot_user = client.invoke(&tl::functions::bots::CreateBot {
                via_deeplink: false,
                name: format!("{}'s Cineforge Streamer", user.first_name),
                username: candidate_username.clone(),
                manager_id: manager_input_user,
            }).await.map_err(|e| format!("Failed to create personal managed bot in Telegram: {e}"))?;

            let (bot_id, bot_access_hash) = match bot_user {
                tl::enums::User::User(u) => (u.id, u.access_hash.unwrap_or(0)),
                tl::enums::User::Empty(e) => (e.id, 0),
            };

            // Register newly created bot in the durable provisioner database
            let register_url = format!("{}/api/provision/register", self.provisioning_url);
            let reg_resp = self
                .client
                .post(&register_url)
                .json(&RegisterBotRequest {
                    challenge_nonce: challenge.challenge_nonce.clone(),
                    bot_id,
                    bot_access_hash,
                    bot_username: candidate_username.clone(),
                })
                .send()
                .await
                .map_err(|e| format!("Failed to register managed bot with provisioning service: {e}"))?;

            if !reg_resp.status().is_success() {
                let body = reg_resp.text().await.unwrap_or_default();
                return Err(format!("Provisioning service failed to register new bot: {body}"));
            }
        }

        // 5. Retrieve personal streamer bot token securely
        let token_url = format!("{}/api/provision/token", self.provisioning_url);
        let token_resp = self
            .client
            .post(&token_url)
            .json(&TokenRequest {
                challenge_nonce: challenge.challenge_nonce,
            })
            .send()
            .await
            .map_err(|e| format!("Failed to export bot token from provisioning service: {e}"))?;

        if !token_resp.status().is_success() {
            let status = token_resp.status();
            let body = token_resp.text().await.unwrap_or_default();
            return Err(format!("Provisioning service refused token export (HTTP {status}): {body}"));
        }

        let token_data: TokenResponse = token_resp
            .json()
            .await
            .map_err(|e| format!("Invalid token response from provisioning service: {e}"))?;

        // 6. Cache durable mapping locally in DPAPI storage
        let mapping = PersonalBotMapping {
            user_id: user.id,
            bot_id: token_data.bot_id,
            bot_username: token_data.bot_username.clone(),
            bot_access_hash: 0,
            created_at: {
                use std::time::SystemTime;
                SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs() as i64
            },
        };
        if let Ok(bytes) = serde_json::to_vec(&mapping) {
            let _ = storage::save_encrypted_bot_mapping(&bytes);
        }

        // 7. Store runtime token strictly in memory
        *self.runtime_bot_token.write().await = Some(token_data.bot_token);
        let bot_info = PersonalBotInfo {
            bot_id: token_data.bot_id,
            bot_username: token_data.bot_username,
            status: "ready".to_string(),
        };
        *self.active_bot_info.write().await = Some(bot_info.clone());

        Ok(bot_info)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_provisioning_and_runtime_token_lifecycle() {
        let service = BotProvisioningService::new_mock(
            12345678,
            "cf_test_streamer_bot",
            "12345678:MOCK_TOKEN",
        );

        let user = TelegramUserInfo {
            id: 99999,
            first_name: "Tester".to_string(),
            last_name: None,
            username: Some("tester".to_string()),
            phone: None,
            is_premium: false,
        };

        // 1. Ensure provisioned
        let info = service.ensure_bot_provisioned(&user, None).await.unwrap();
        assert_eq!(info.bot_id, 12345678);
        assert_eq!(info.bot_username, "cf_test_streamer_bot");
        assert_eq!(info.status, "ready");

        // 2. Verify runtime token is in memory
        let token = service.get_runtime_token().await;
        assert_eq!(token, Some("12345678:MOCK_TOKEN".to_string()));

        // 3. Clear runtime tokens on logout
        service.clear_runtime_tokens().await;
        let token_after = service.get_runtime_token().await;
        assert_eq!(token_after, None);
    }

    #[test]
    fn test_validate_provisioning_url_https_and_dev_rules() {
        // Production HTTPS - allowed
        assert!(validate_provisioning_url("https://provision.cineforge.app", false).is_ok());
        assert!(validate_provisioning_url("https://api.mycustomdomain.com/provision", false).is_ok());

        // Local loopback HTTP in production - allowed for local developer convenience
        assert!(validate_provisioning_url("http://127.0.0.1:8085", false).is_ok());
        assert!(validate_provisioning_url("http://localhost:8085", false).is_ok());
        assert!(validate_provisioning_url("http://[::1]:8085", false).is_ok());

        // Insecure remote HTTP in production - REJECTED
        let prod_err = validate_provisioning_url("http://provision.cineforge.app", false);
        assert!(prod_err.is_err());
        assert!(prod_err.unwrap_err().contains("must use HTTPS in production"));

        let remote_http = validate_provisioning_url("http://192.168.1.100:8085", false);
        assert!(remote_http.is_err());

        // Insecure remote HTTP in explicit dev mode - permitted
        assert!(validate_provisioning_url("http://provision.cineforge.app", true).is_ok());

        // Malformed or empty URLs - REJECTED
        assert!(validate_provisioning_url("", false).is_err());
        assert!(validate_provisioning_url("   ", false).is_err());
        assert!(validate_provisioning_url("not_a_valid_url", false).is_err());
    }
}
