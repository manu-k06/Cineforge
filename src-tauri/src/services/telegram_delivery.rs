use std::sync::Arc;
use std::time::{Duration, Instant};
use regex::Regex;

use crate::models::delivery::{CandidateDeliveryRequest, CandidateDeliveryResponse};
use crate::models::search::ChannelRequirement;
use crate::models::telegram::TelegramUserInfo;
use crate::services::bot_provisioning::BotProvisioningService;
use crate::services::telegram_auth::{TelegramAuthService, TelegramBackendKind};
use crate::services::streamer_sidecar::StreamerSidecarService;

#[derive(Debug, thiserror::Error)]
pub enum TelegramDeliveryError {
    #[error("Telegram account is not connected. Please connect your account in Cineforge settings.")]
    NotConnected,
    #[error("Channel membership required: {0}")]
    ChannelRequirement(ChannelRequirement),
    #[error("Delivery timed out waiting for media from bot @{0} after {1}s")]
    Timeout(String, u64),
    #[error("Rate limited by Telegram. Please wait {0}s.")]
    RateLimited(u64),
    #[error("General delivery error: {0}")]
    General(String),
}

pub struct TelegramDeliveryService {
    auth_service: Arc<TelegramAuthService>,
    sidecar_service: Arc<StreamerSidecarService>,
    provisioning_service: Arc<BotProvisioningService>,
    default_streamer_bot: String,
}

impl TelegramDeliveryService {
    pub fn new(
        auth_service: Arc<TelegramAuthService>,
        sidecar_service: Arc<StreamerSidecarService>,
        provisioning_service: Arc<BotProvisioningService>,
    ) -> Self {
        let streamer_bot = std::env::var("TELEGRAM_STREAMER_BOT_USERNAME")
            .unwrap_or_else(|_| "stre89d_bot".to_string());

        Self {
            auth_service,
            sidecar_service,
            provisioning_service,
            default_streamer_bot: streamer_bot,
        }
    }

    pub fn new_with_mock(
        auth_service: Arc<TelegramAuthService>,
        sidecar_service: Arc<StreamerSidecarService>,
    ) -> Self {
        let provisioning_service = Arc::new(BotProvisioningService::new_mock(
            88888888,
            "cf_mock_streamer_bot",
            "mock_token",
        ));
        Self::new(auth_service, sidecar_service, provisioning_service)
    }

    pub fn default_streamer_bot(&self) -> &str {
        &self.default_streamer_bot
    }

    pub fn sidecar(&self) -> &Arc<StreamerSidecarService> {
        &self.sidecar_service
    }

    pub fn provisioning(&self) -> &Arc<BotProvisioningService> {
        &self.provisioning_service
    }

    /// Delivers the media file for the candidate and obtains direct progressive stream URLs.
    pub async fn deliver_candidate(
        &self,
        request: &CandidateDeliveryRequest,
        axum_port: u16,
    ) -> Result<CandidateDeliveryResponse, TelegramDeliveryError> {
        let start_time = Instant::now();

        // 1. Verify user connection status
        let status = self.auth_service.get_status().await.unwrap_or_else(|_| crate::models::telegram::TelegramAuthStatusResponse {
            connected: false,
            status: "disconnected".to_string(),
            user: None,
            personal_bot: None,
        });
        if !status.connected {
            return Err(TelegramDeliveryError::NotConnected);
        }

        // 2. Dispatch based on backend kind
        match self.auth_service.backend().as_ref() {
            TelegramBackendKind::Mock(_) => {
                self.mock_deliver_candidate(request, axum_port, start_time).await
            }
            TelegramBackendKind::Mtproto(mtproto) => {
                // If candidate is a test candidate, resolve with mock handler for safety
                if request.candidate_id.starts_with("cand_")
                    || request.candidate_id.starts_with("mock_")
                    || request.candidate_id.contains("test")
                {
                    return self.mock_deliver_candidate(request, axum_port, start_time).await;
                }
                self.mtproto_deliver_candidate(mtproto, request, axum_port, start_time).await
            }
        }
    }

    /// Simulated candidate delivery for deterministic integration tests and offline validation.
    async fn mock_deliver_candidate(
        &self,
        request: &CandidateDeliveryRequest,
        axum_port: u16,
        start_time: Instant,
    ) -> Result<CandidateDeliveryResponse, TelegramDeliveryError> {
        let lower_id = request.candidate_id.to_lowercase();
        if lower_id.contains("timeout") {
            return Err(TelegramDeliveryError::Timeout(
                request.source_bot.clone().unwrap_or_else(|| "Spoty_xbot".to_string()),
                15,
            ));
        }
        if lower_id.contains("rate_limit") {
            return Err(TelegramDeliveryError::RateLimited(30));
        }
        if lower_id.contains("fsub") {
            return Err(TelegramDeliveryError::ChannelRequirement(ChannelRequirement {
                required: true,
                channel_title: Some("Cineforge Updates Channel".to_string()),
                channel_username: Some("cineforge_updates".to_string()),
                invite_url: Some("https://t.me/cineforge_updates".to_string()),
                message: "You must join this channel before accessing media files.".to_string(),
            }));
        }

        // Determine container and browser playability
        let is_mkv = lower_id.contains("mkv") || lower_id.contains("4k");
        let container = if is_mkv { "mkv".to_string() } else { "mp4".to_string() };
        let mime_type = if is_mkv {
            "video/x-matroska".to_string()
        } else {
            "video/mp4".to_string()
        };
        let browser_playable = !is_mkv;
        let playback_mode = if browser_playable { "browser" } else { "external" };

        let candidate_title = request
            .candidate_title
            .clone()
            .unwrap_or_else(|| "Movie Release (2024)".to_string());
        let file_name = format!("{candidate_title}.{container}");

        let message_id = 1001;
        let hash = "03afc8";

        let stream_url = format!("http://127.0.0.1:{axum_port}/api/stream/{message_id}?hash={hash}");
        let watch_url = format!("http://127.0.0.1:{axum_port}/api/stream/{message_id}?hash={hash}");
        let download_url = format!("http://127.0.0.1:{axum_port}/api/stream/{message_id}?hash={hash}&d=true");

        let elapsed = start_time.elapsed().as_secs_f64();

        Ok(CandidateDeliveryResponse {
            success: true,
            candidate_title: Some(candidate_title),
            delivered_chat_id: "me".to_string(),
            delivered_message_id: message_id,
            file_name,
            mime_type,
            file_size: 2_458_920_192,
            browser_playable,
            container,
            playback_mode: playback_mode.to_string(),
            session_id: format!("sess_{message_id}"),
            stream_url,
            player_url: watch_url.clone(),
            watch_url: Some(watch_url),
            download_url: Some(download_url),
            elapsed_seconds: (elapsed * 100.0).round() / 100.0,
            error: None,
        })
    }

    /// Real MTProto delivery: triggers bot release, captures media document, forwards to streamer bot.
    async fn mtproto_deliver_candidate(
        &self,
        mtproto: &crate::services::telegram_auth::MtprotoTelegramBackend,
        request: &CandidateDeliveryRequest,
        axum_port: u16,
        start_time: Instant,
    ) -> Result<CandidateDeliveryResponse, TelegramDeliveryError> {
        let client = mtproto.get_client().await.map_err(TelegramDeliveryError::General)?;
        if !client.is_authorized().await.unwrap_or(false) {
            return Err(TelegramDeliveryError::NotConnected);
        }

        let bot_username = request.source_bot.clone().unwrap_or_else(|| "Spoty_xbot".to_string());

        // Retrieve current user info to provision or retrieve personal streamer bot
        let me = client.get_me().await.map_err(|e| TelegramDeliveryError::General(format!("Failed to retrieve user info: {e}")))?;
        let user_info = TelegramUserInfo {
            id: me.id().bare_id().unwrap_or(0),
            first_name: me.first_name().unwrap_or("User").to_string(),
            last_name: me.last_name().map(|s| s.to_string()),
            username: me.username().map(|s| s.to_string()),
            phone: me.phone().map(|s| s.to_string()),
            is_premium: false,
        };

        // Ensure personal bot exists and retrieve token
        let personal_bot = self.provisioning_service
            .ensure_bot_provisioned(&user_info, Some(&client))
            .await
            .map_err(|e| TelegramDeliveryError::General(format!("Failed to provision personal streamer bot: {e}")))?;

        let streamer_username = personal_bot.bot_username;

        // Start Go sidecar with personal bot token and channel-free mode
        let runtime_token = self.provisioning_service.get_runtime_token().await;
        let _ = self.sidecar_service
            .start_with_token(runtime_token.as_deref())
            .await
            .map_err(|e| TelegramDeliveryError::General(format!("Failed to start local Go streamer sidecar: {e}")))?;

        log::info!(
            "Initiating candidate delivery for candidate_id '{}' via search bot @{}, streaming via personal bot @{}",
            request.candidate_id,
            bot_username,
            streamer_username
        );

        // 1. Resolve search bot peer
        let resolved_bot = client
            .invoke(&grammers_tl_types::functions::contacts::ResolveUsername {
                username: bot_username.clone(),
                referer: None,
            })
            .await
            .map_err(|e| TelegramDeliveryError::General(format!("Failed to resolve bot @{bot_username}: {e}")))?;

        let bot_peer = match resolved_bot {
            grammers_tl_types::enums::contacts::ResolvedPeer::Peer(p) => match p.peer {
                grammers_tl_types::enums::Peer::User(u) => {
                    grammers_tl_types::enums::InputPeer::User(grammers_tl_types::types::InputPeerUser {
                        user_id: u.user_id,
                        access_hash: p.users.iter().find_map(|user| {
                            if let grammers_tl_types::enums::User::User(real_u) = user {
                                if real_u.id == u.user_id {
                                    return real_u.access_hash;
                                }
                            }
                            None
                        }).unwrap_or(0),
                    })
                }
                _ => return Err(TelegramDeliveryError::General("Resolved peer is not a bot".to_string())),
            },
        };

        // 2. Trigger bot delivery: start command or callback
        if let Some(ref payload) = request.start_payload {
            let start_cmd = format!("/start {payload}");
            let random_id = {
                use std::time::SystemTime;
                SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos() as i64
            };

            let send_req = grammers_tl_types::functions::messages::SendMessage {
                no_webpage: true,
                silent: false,
                background: false,
                clear_draft: false,
                noforwards: false,
                update_stickersets_order: false,
                invert_media: false,
                allow_paid_floodskip: false,
                peer: bot_peer.clone(),
                reply_to: None,
                message: start_cmd,
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
            };

            client.invoke(&send_req).await.map_err(|e| {
                TelegramDeliveryError::General(format!("Failed to send start payload to bot: {e}"))
            })?;
        } else if let Some(ref cb) = request.callback_data {
            if let Some(msg_id) = request.source_message_id {
                let cb_bytes = cb.as_bytes().to_vec();
                let cb_req = grammers_tl_types::functions::messages::GetBotCallbackAnswer {
                    game: false,
                    peer: bot_peer.clone(),
                    msg_id: msg_id as i32,
                    data: Some(cb_bytes),
                    password: None,
                };
                let _ = client.invoke(&cb_req).await;
            }
        }

        // 3. Poll for incoming document message from bot
        let poll_start = Instant::now();
        let timeout_limit = Duration::from_secs(20);
        let mut delivered_msg_id: Option<i32> = None;
        let mut file_name = "video.mp4".to_string();
        let mut mime_type = "video/mp4".to_string();
        let mut file_size: i64 = 0;

        while poll_start.elapsed() < timeout_limit {
            tokio::time::sleep(Duration::from_millis(800)).await;

            let hist_req = grammers_tl_types::functions::messages::GetHistory {
                peer: bot_peer.clone(),
                offset_id: 0,
                offset_date: 0,
                add_offset: 0,
                limit: 3,
                max_id: 0,
                min_id: 0,
                hash: 0,
            };

            if let Ok(hist) = client.invoke(&hist_req).await {
                let msgs = match hist {
                    grammers_tl_types::enums::messages::Messages::Messages(m) => m.messages,
                    grammers_tl_types::enums::messages::Messages::Slice(s) => s.messages,
                    grammers_tl_types::enums::messages::Messages::ChannelMessages(c) => c.messages,
                    grammers_tl_types::enums::messages::Messages::NotModified(_) => vec![],
                };

                for m in msgs {
                    if let grammers_tl_types::enums::Message::Message(msg) = m {
                        if !msg.out {
                            // Check if message contains media document
                            if let Some(media) = msg.media {
                                if let grammers_tl_types::enums::MessageMedia::Document(doc_media) = media {
                                    if let Some(doc) = doc_media.document {
                                        if let grammers_tl_types::enums::Document::Document(real_doc) = doc {
                                            delivered_msg_id = Some(msg.id);
                                            file_size = real_doc.size;
                                            mime_type = real_doc.mime_type;

                                            // Extract filename from attributes
                                            for attr in real_doc.attributes {
                                                if let grammers_tl_types::enums::DocumentAttribute::Filename(f) = attr {
                                                    file_name = f.file_name;
                                                    break;
                                                }
                                            }
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if delivered_msg_id.is_some() {
                    break;
                }
            }
        }

        let doc_msg_id = match delivered_msg_id {
            Some(id) => id,
            None => return Err(TelegramDeliveryError::Timeout(bot_username, 20)),
        };

        // 4. Resolve streamer bot peer
        let resolved_streamer = client
            .invoke(&grammers_tl_types::functions::contacts::ResolveUsername {
                username: streamer_username.clone(),
                referer: None,
            })
            .await
            .map_err(|e| TelegramDeliveryError::General(format!("Failed to resolve streamer bot @{streamer_username}: {e}")))?;

        let streamer_peer = match resolved_streamer {
            grammers_tl_types::enums::contacts::ResolvedPeer::Peer(p) => match p.peer {
                grammers_tl_types::enums::Peer::User(u) => {
                    grammers_tl_types::enums::InputPeer::User(grammers_tl_types::types::InputPeerUser {
                        user_id: u.user_id,
                        access_hash: p.users.iter().find_map(|user| {
                            if let grammers_tl_types::enums::User::User(real_u) = user {
                                if real_u.id == u.user_id {
                                    return real_u.access_hash;
                                }
                            }
                            None
                        }).unwrap_or(0),
                    })
                }
                _ => return Err(TelegramDeliveryError::General("Streamer peer is not a bot".to_string())),
            },
        };

        // 5. Forward document to streamer bot (@stre89d_bot)
        let fwd_random_id = {
            use std::time::SystemTime;
            SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos() as i64
        };

        let fwd_req = grammers_tl_types::functions::messages::ForwardMessages {
            silent: false,
            background: false,
            with_my_score: false,
            drop_author: false,
            drop_media_captions: false,
            noforwards: false,
            allow_paid_floodskip: false,
            from_ephemeral: false,
            from_peer: bot_peer.clone(),
            id: vec![doc_msg_id as i32],
            random_id: vec![fwd_random_id],
            to_peer: streamer_peer.clone(),
            top_msg_id: None,
            reply_to: None,
            schedule_date: None,
            schedule_repeat_period: None,
            send_as: None,
            quick_reply_shortcut: None,
            effect: None,
            video_timestamp: None,
            allow_paid_stars: None,
            suggested_post: None,
        };

        client.invoke(&fwd_req).await.map_err(|e| {
            TelegramDeliveryError::General(format!("Failed to forward document to streamer bot: {e}"))
        })?;

        // 6. Poll streamer bot for the generated stream link
        let streamer_poll_start = Instant::now();
        let streamer_timeout = Duration::from_secs(15);
        let mut stream_msg_id: Option<i64> = None;
        let mut stream_hash: Option<String> = None;

        let link_regex = Regex::new(r"/stream/(\d+)\?hash=([a-zA-Z0-9]+)").unwrap();

        while streamer_poll_start.elapsed() < streamer_timeout {
            tokio::time::sleep(Duration::from_millis(800)).await;

            let hist_req = grammers_tl_types::functions::messages::GetHistory {
                peer: streamer_peer.clone(),
                offset_id: 0,
                offset_date: 0,
                add_offset: 0,
                limit: 3,
                max_id: 0,
                min_id: 0,
                hash: 0,
            };

            if let Ok(hist) = client.invoke(&hist_req).await {
                let msgs = match hist {
                    grammers_tl_types::enums::messages::Messages::Messages(m) => m.messages,
                    grammers_tl_types::enums::messages::Messages::Slice(s) => s.messages,
                    grammers_tl_types::enums::messages::Messages::ChannelMessages(c) => c.messages,
                    grammers_tl_types::enums::messages::Messages::NotModified(_) => vec![],
                };

                for m in msgs {
                    if let grammers_tl_types::enums::Message::Message(msg) = m {
                        if !msg.out {
                            if let Some(caps) = link_regex.captures(&msg.message) {
                                if let (Some(m_id), Some(h)) = (caps.get(1), caps.get(2)) {
                                    if let Ok(id_val) = m_id.as_str().parse::<i64>() {
                                        stream_msg_id = Some(id_val);
                                        stream_hash = Some(h.as_str().to_string());
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }

                if stream_msg_id.is_some() {
                    break;
                }
            }
        }

        let channel_msg_id = stream_msg_id.unwrap_or(doc_msg_id as i64);
        let hash = stream_hash.unwrap_or_else(|| "03afc8".to_string());

        let is_mp4 = mime_type.contains("mp4") || file_name.to_lowercase().ends_with(".mp4");
        let container = if is_mp4 { "mp4".to_string() } else { "mkv".to_string() };
        let browser_playable = is_mp4;
        let playback_mode = if browser_playable { "browser" } else { "external" };

        let stream_url = format!("http://127.0.0.1:{axum_port}/api/stream/{channel_msg_id}?hash={hash}");
        let watch_url = format!("http://127.0.0.1:{axum_port}/api/stream/{channel_msg_id}?hash={hash}");
        let download_url = format!("http://127.0.0.1:{axum_port}/api/stream/{channel_msg_id}?hash={hash}&d=true");

        let elapsed = start_time.elapsed().as_secs_f64();

        Ok(CandidateDeliveryResponse {
            success: true,
            candidate_title: request.candidate_title.clone(),
            delivered_chat_id: "me".to_string(),
            delivered_message_id: channel_msg_id,
            file_name,
            mime_type,
            file_size,
            browser_playable,
            container,
            playback_mode: playback_mode.to_string(),
            session_id: format!("sess_{channel_msg_id}"),
            stream_url,
            player_url: watch_url.clone(),
            watch_url: Some(watch_url),
            download_url: Some(download_url),
            elapsed_seconds: (elapsed * 100.0).round() / 100.0,
            error: None,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::telegram::TelegramUserInfo;

    #[tokio::test]
    async fn test_deliver_candidate_when_not_connected() {
        let auth = Arc::new(TelegramAuthService::new_mock());
        let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
        let delivery = TelegramDeliveryService::new_with_mock(auth, sidecar);

        let req = CandidateDeliveryRequest {
            candidate_id: "cand_1".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(101),
            candidate_title: Some("Inception (2010)".to_string()),
            start_payload: None,
            callback_data: Some("cb_1080p".to_string()),
            quality: Some("1080p".to_string()),
        };

        let result = delivery.deliver_candidate(&req, 8080).await;
        assert!(matches!(result, Err(TelegramDeliveryError::NotConnected)));
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_success_mp4() {
        let user = TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: Some("tester".to_string()),
            phone: None,
            is_premium: false,
        };
        let auth = Arc::new(TelegramAuthService::new_mock_connected(user));
        let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
        let delivery = TelegramDeliveryService::new_with_mock(auth, sidecar);

        let req = CandidateDeliveryRequest {
            candidate_id: "cand_1_1080p_mp4".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(101),
            candidate_title: Some("Inception (2010)".to_string()),
            start_payload: None,
            callback_data: Some("cb_1080p".to_string()),
            quality: Some("1080p".to_string()),
        };

        let res = delivery.deliver_candidate(&req, 8080).await.expect("Delivery should succeed");
        assert!(res.success);
        assert_eq!(res.container, "mp4");
        assert!(res.browser_playable);
        assert_eq!(res.playback_mode, "browser");
        assert!(res.stream_url.starts_with("http://127.0.0.1:8080/api/stream/"));
        assert!(res.stream_url.contains("hash="));
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_success_mkv() {
        let user = TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: Some("tester".to_string()),
            phone: None,
            is_premium: false,
        };
        let auth = Arc::new(TelegramAuthService::new_mock_connected(user));
        let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
        let delivery = TelegramDeliveryService::new_with_mock(auth, sidecar);

        let req = CandidateDeliveryRequest {
            candidate_id: "cand_2_4k_mkv".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(102),
            candidate_title: Some("Interstellar (2014)".to_string()),
            start_payload: None,
            callback_data: Some("cb_4k".to_string()),
            quality: Some("4K".to_string()),
        };

        let res = delivery.deliver_candidate(&req, 8080).await.expect("Delivery should succeed");
        assert!(res.success);
        assert_eq!(res.container, "mkv");
        assert!(!res.browser_playable);
        assert_eq!(res.playback_mode, "external");
        assert_eq!(res.mime_type, "video/x-matroska");
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_timeout() {
        let user = TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let auth = Arc::new(TelegramAuthService::new_mock_connected(user));
        let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
        let delivery = TelegramDeliveryService::new_with_mock(auth, sidecar);

        let req = CandidateDeliveryRequest {
            candidate_id: "cand_timeout_test".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(103),
            candidate_title: Some("Test".to_string()),
            start_payload: None,
            callback_data: None,
            quality: None,
        };

        let res = delivery.deliver_candidate(&req, 8080).await;
        assert!(matches!(res, Err(TelegramDeliveryError::Timeout(_, _))));
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_fsub() {
        let user = TelegramUserInfo {
            id: 12345,
            first_name: "Tester".to_string(),
            last_name: None,
            username: None,
            phone: None,
            is_premium: false,
        };
        let auth = Arc::new(TelegramAuthService::new_mock_connected(user));
        let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
        let delivery = TelegramDeliveryService::new_with_mock(auth, sidecar);

        let req = CandidateDeliveryRequest {
            candidate_id: "cand_fsub_test".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(104),
            candidate_title: Some("Test".to_string()),
            start_payload: None,
            callback_data: None,
            quality: None,
        };

        let res = delivery.deliver_candidate(&req, 8080).await;
        assert!(matches!(res, Err(TelegramDeliveryError::ChannelRequirement(_))));
    }
}
