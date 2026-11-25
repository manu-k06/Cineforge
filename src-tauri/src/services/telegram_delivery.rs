use std::collections::HashSet;
use std::sync::{Arc, LazyLock};
use std::time::{Duration, Instant};
use regex::Regex;

use crate::models::delivery::{CandidateDeliveryRequest, CandidateDeliveryResponse};
use crate::models::search::ChannelRequirement;
use crate::models::telegram::TelegramUserInfo;
use crate::services::bot_provisioning::BotProvisioningService;
use crate::services::telegram_auth::{TelegramAuthService, TelegramBackendKind};
use crate::services::streamer_sidecar::StreamerSidecarService;
use crate::services::telegram_search_parser::{
    detect_channel_requirement, detect_unavailable_file_message, parse_channel_link,
    ParsedChannelTarget, RawInlineButton,
};

static FLOOD_WAIT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)FLOOD_WAIT(?:_|\D+)(\d+)").unwrap());

fn extract_flood_wait_seconds(err_str: &str) -> Option<u64> {
    FLOOD_WAIT_RE
        .captures(err_str)
        .and_then(|c| c.get(1))
        .and_then(|m| m.as_str().parse::<u64>().ok())
}

/// Result outcome from attempting to join a public or private Telegram channel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum JoinChannelOutcome {
    JoinedPublic(String),
    JoinedPrivate(String),
    AlreadyParticipant,
    RequestSent,
}

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
    #[error("{0}")]
    FileUnavailable(String),
    #[error("General delivery error: {0}")]
    General(String),
}

fn extract_buttons_from_reply_markup(
    markup: &grammers_tl_types::enums::ReplyMarkup,
) -> Vec<RawInlineButton> {
    let mut raw_buttons = Vec::new();
    if let grammers_tl_types::enums::ReplyMarkup::ReplyInlineMarkup(inline) = markup {
        for row in &inline.rows {
            let grammers_tl_types::enums::KeyboardInlineButtonRow::Row(r) = row;
            for btn in &r.buttons {
                let grammers_tl_types::enums::KeyboardInlineButton::Button(b) = btn;
                match &b.r#type {
                    grammers_tl_types::enums::InlineButtonType::Callback(cb) => {
                        let cb_str = String::from_utf8_lossy(&cb.data).to_string();
                        raw_buttons.push(RawInlineButton {
                            text: b.text.clone(),
                            callback_data: Some(cb_str),
                            url: None,
                        });
                    }
                    grammers_tl_types::enums::InlineButtonType::Url(u) => {
                        raw_buttons.push(RawInlineButton {
                            text: b.text.clone(),
                            callback_data: None,
                            url: Some(u.url.clone()),
                        });
                    }
                    _ => {}
                }
            }
        }
    }
    raw_buttons
}

#[derive(Debug, Clone)]
struct BotMediaDoc {
    pub file_name: String,
    pub mime_type: String,
    pub file_size: i64,
    pub is_sticker: bool,
}

#[derive(Debug, Clone)]
struct BotChatMessage {
    pub id: i32,
    pub out: bool,
    pub edit_date: Option<i32>,
    pub text: String,
    pub buttons: Vec<RawInlineButton>,
    pub media_doc: Option<BotMediaDoc>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct CapturedMedia {
    pub msg_id: i32,
    pub file_name: String,
    pub mime_type: String,
    pub file_size: i64,
}

fn extract_bot_chat_message(m: &grammers_tl_types::enums::Message) -> Option<BotChatMessage> {
    let grammers_tl_types::enums::Message::Message(msg) = m else {
        return None;
    };

    let buttons = msg
        .reply_markup
        .as_ref()
        .map(extract_buttons_from_reply_markup)
        .unwrap_or_default();

    let mut media_doc = None;
    if let Some(grammers_tl_types::enums::MessageMedia::Document(ref doc_media)) = msg.media {
        if let Some(grammers_tl_types::enums::Document::Document(ref real_doc)) = doc_media.document {
            let mut file_name = "video.mp4".to_string();
            let mut is_sticker = real_doc.mime_type == "image/webp"
                || real_doc.mime_type == "application/x-tgsticker";

            for attr in &real_doc.attributes {
                match attr {
                    grammers_tl_types::enums::DocumentAttribute::Filename(f) => {
                        file_name = f.file_name.clone();
                    }
                    grammers_tl_types::enums::DocumentAttribute::Sticker(_) => {
                        is_sticker = true;
                    }
                    _ => {}
                }
            }

            media_doc = Some(BotMediaDoc {
                file_name,
                mime_type: real_doc.mime_type.clone(),
                file_size: real_doc.size,
                is_sticker,
            });
        }
    }

    Some(BotChatMessage {
        id: msg.id,
        out: msg.out,
        edit_date: msg.edit_date,
        text: msg.message.clone(),
        buttons,
        media_doc,
    })
}

/// Ensures we never confuse an FSub gate sticker, thumbnail, or promotional banner with the video file.
fn is_genuine_media_doc(msg: &BotChatMessage, doc: &BotMediaDoc, bot_username: &str) -> bool {
    if doc.is_sticker {
        return false;
    }

    let lower_mime = doc.mime_type.to_lowercase();
    let lower_name = doc.file_name.to_lowercase();
    let has_video_ext = lower_name.ends_with(".mp4")
        || lower_name.ends_with(".mkv")
        || lower_name.ends_with(".avi")
        || lower_name.ends_with(".mov")
        || lower_name.ends_with(".webm")
        || lower_name.ends_with(".ts")
        || lower_name.ends_with(".m4v");
    let is_video_mime = lower_mime.starts_with("video/");

    if lower_mime.starts_with("image/") && !has_video_ext {
        return false;
    }

    if !is_video_mime
        && !has_video_ext
        && doc.file_size < 1_000_000
        && detect_channel_requirement(&msg.text, &msg.buttons, Some(bot_username)).is_some()
    {
        return false;
    }

    true
}

trait BotDeliverySession {
    async fn send_start(&mut self, payload: &str) -> Result<(), TelegramDeliveryError>;
    async fn click_callback(
        &mut self,
        msg_id: i32,
        data: &str,
    ) -> Result<Option<String>, TelegramDeliveryError>;
    async fn get_recent_messages(
        &mut self,
        limit: i32,
    ) -> Result<Vec<BotChatMessage>, TelegramDeliveryError>;
    async fn join_channel(&mut self, url: &str) -> Result<JoinChannelOutcome, TelegramDeliveryError>;
    async fn sleep_ms(&mut self, ms: u64);
}

/// Shared bot delivery and automated Force-Subscription (FSub) resolution engine.
/// Mirrors `backend/app/services/telegram.py` (`resolve_fsub_gate` + `deliver_candidate`):
/// triggers candidate delivery, detects membership gates, auto-joins only valid Telegram
/// channel links extracted from the gate message, waits 2.5s for membership sync, activates
/// the gate's Try Again callback or /start retry payload, and captures genuine media.
async fn resolve_and_capture_media<S: BotDeliverySession>(
    session: &mut S,
    request: &CandidateDeliveryRequest,
    bot_username: &str,
) -> Result<CapturedMedia, TelegramDeliveryError> {
    const MAX_GATE_RETRIES: usize = 2;
    const INITIAL_MEDIA_WAIT_SECS: u64 = 20;
    const RETRY_MEDIA_WAIT_SECS: u64 = 20;
    const MAX_TOTAL_WAIT_SECS: u64 = 55;
    const MAX_POLL_ITERATIONS: usize = 65;

    // 1. Capture baseline message ID / edit signature before triggering the bot
    let initial_msgs = session.get_recent_messages(5).await.unwrap_or_default();
    let mut min_poll_msg_id: i32 = initial_msgs.iter().map(|m| m.id).max().unwrap_or(0);
    let baseline_edit_sig: Option<(i32, Option<i32>, String)> =
        request.source_message_id.and_then(|src_id| {
            initial_msgs
                .iter()
                .find(|m| m.id as i64 == src_id)
                .map(|m| (m.id, m.edit_date, format!("{}|{:?}", m.text, m.buttons)))
        });

    // 2. Trigger initial candidate request via /start payload or inline callback
    if let Some(ref payload) = request.start_payload {
        session.send_start(payload).await?;
    } else if let (Some(cb), Some(msg_id)) = (&request.callback_data, request.source_message_id) {
        let _ = session.click_callback(msg_id as i32, cb).await?;
    } else {
        return Err(TelegramDeliveryError::General(
            "Neither start_payload nor callback_data was provided for candidate delivery."
                .to_string(),
        ));
    }

    // 3. Poll for media document while automatically resolving bounded FSub gates
    let overall_start = Instant::now();
    let mut step_start = Instant::now();
    let mut step_timeout = Duration::from_secs(INITIAL_MEDIA_WAIT_SECS);
    let mut gate_attempts: usize = 0;
    let mut handled_gates: HashSet<(i32, String)> = HashSet::new();
    let mut watched_callback_gate_id: Option<i32> = None;
    let mut last_callback_alert: Option<String> = None;
    let mut poll_iterations: usize = 0;

    while step_start.elapsed() < step_timeout
        && overall_start.elapsed() < Duration::from_secs(MAX_TOTAL_WAIT_SECS)
        && poll_iterations < MAX_POLL_ITERATIONS
    {
        poll_iterations += 1;
        session.sleep_ms(800).await;

        let msgs = match session.get_recent_messages(5).await {
            Ok(m) => m,
            Err(_) => continue,
        };

        let highest_seen_id = msgs.iter().map(|m| m.id).max().unwrap_or(min_poll_msg_id);

        let relevant_incoming: Vec<&BotChatMessage> = msgs
            .iter()
            .filter(|m| {
                if m.out {
                    return false;
                }
                if m.id > min_poll_msg_id {
                    return true;
                }
                if watched_callback_gate_id == Some(m.id) {
                    return true;
                }
                if request.callback_data.is_some() {
                    if let Some((base_id, base_edit, ref base_sig)) = baseline_edit_sig {
                        if m.id == base_id {
                            let cur_sig = format!("{}|{:?}", m.text, m.buttons);
                            return m.edit_date != base_edit || cur_sig != *base_sig;
                        }
                    }
                }
                false
            })
            .collect();

        // Pass 1: Capture any genuine media document first
        for m in &relevant_incoming {
            if let Some(ref doc) = m.media_doc {
                if is_genuine_media_doc(m, doc, bot_username) {
                    return Ok(CapturedMedia {
                        msg_id: m.id,
                        file_name: doc.file_name.clone(),
                        mime_type: doc.mime_type.clone(),
                        file_size: doc.file_size,
                    });
                }
            }
        }

        // Pass 2: Inspect the newest incoming non-media message for an FSub gate
        if let Some(newest_msg) = relevant_incoming.iter().copied().max_by_key(|m| m.id) {
            if let Some(gate) =
                detect_channel_requirement(&newest_msg.text, &newest_msg.buttons, Some(bot_username))
            {
                let gate_sig = format!(
                    "{:?}|{:?}|{:?}|{}|{}",
                    gate.all_channel_urls(),
                    gate.retry_callback,
                    gate.retry_start_payload,
                    newest_msg.edit_date.unwrap_or(0),
                    newest_msg.text
                );

                // Avoid re-triggering the exact same gate while waiting for the bot's reply
                if handled_gates.contains(&(newest_msg.id, gate_sig.clone())) {
                    continue;
                }

                if gate_attempts >= MAX_GATE_RETRIES {
                    let alert_suffix = last_callback_alert
                        .as_deref()
                        .map(|a| format!(" Bot replied: {a}"))
                        .unwrap_or_default();
                    return Err(TelegramDeliveryError::General(format!(
                        "Bot @{bot_username} still requires channel membership after {MAX_GATE_RETRIES} automatic join attempts.{alert_suffix} Please join the required channel in Telegram and try again."
                    )));
                }

                gate_attempts += 1;
                handled_gates.insert((newest_msg.id, gate_sig));

                let target_urls = gate.all_channel_urls();
                if target_urls.is_empty() {
                    return Err(TelegramDeliveryError::General(format!(
                        "Bot @{bot_username} requires channel membership, but no valid Telegram channel or invite link was found in its gate message."
                    )));
                }

                log::info!(
                    "Detected FSub gate from @{bot_username} (attempt {gate_attempts}/{MAX_GATE_RETRIES}); auto-joining {} channel(s): {:?}",
                    target_urls.len(),
                    target_urls
                );

                // Join every valid Telegram channel link extracted from this gate message
                for ch_url in &target_urls {
                    match session.join_channel(ch_url).await? {
                        JoinChannelOutcome::RequestSent => {
                            return Err(TelegramDeliveryError::General(format!(
                                "Join request sent for '{ch_url}'. Admin approval is required before @{bot_username} can deliver this file."
                            )));
                        }
                        JoinChannelOutcome::JoinedPublic(u) => {
                            log::info!("Auto-joined public FSub channel @{u}");
                        }
                        JoinChannelOutcome::JoinedPrivate(h) => {
                            log::info!("Auto-joined private FSub channel invite '{h}'");
                        }
                        JoinChannelOutcome::AlreadyParticipant => {
                            log::info!("Already a participant of FSub channel '{ch_url}'");
                        }
                    }
                }

                // Wait for Telegram datacenter getChatMember caches to propagate
                session.sleep_ms(2500).await;

                // Press the gate message's Try Again callback, or send its /start payload to the same bot
                if let Some(ref cb) = gate.retry_callback {
                    log::info!(
                        "Clicking FSub retry callback button '{}' on message {} (@{})",
                        cb,
                        newest_msg.id,
                        bot_username
                    );
                    watched_callback_gate_id = Some(newest_msg.id);
                    match session.click_callback(newest_msg.id, cb).await {
                        Ok(maybe_alert) => {
                            if let Some(alert) = maybe_alert {
                                log::info!("FSub retry callback answer from @{bot_username}: {alert}");
                                last_callback_alert = Some(alert);
                            }
                        }
                        Err(cb_err) => {
                            if let Some(ref payload) = gate.retry_start_payload {
                                log::warn!(
                                    "Retry callback failed ({cb_err}); falling back to /start {payload}"
                                );
                                min_poll_msg_id = highest_seen_id.max(newest_msg.id);
                                session.send_start(payload).await?;
                            } else {
                                return Err(cb_err);
                            }
                        }
                    }
                } else if let Some(ref payload) = gate.retry_start_payload {
                    log::info!(
                        "Sending FSub retry /start payload '{}' to @{}",
                        payload,
                        bot_username
                    );
                    min_poll_msg_id = highest_seen_id.max(newest_msg.id);
                    session.send_start(payload).await?;
                } else if let Some(ref payload) = request.start_payload {
                    log::info!(
                        "Resending initial /start payload '{}' to @{} after FSub join",
                        payload,
                        bot_username
                    );
                    min_poll_msg_id = highest_seen_id.max(newest_msg.id);
                    session.send_start(payload).await?;
                } else if let (Some(cb), Some(src_id)) =
                    (&request.callback_data, request.source_message_id)
                {
                    log::info!(
                        "Re-clicking initial callback '{}' on message {} (@{}) after FSub join",
                        cb,
                        src_id,
                        bot_username
                    );
                    watched_callback_gate_id = Some(src_id as i32);
                    let _ = session.click_callback(src_id as i32, cb).await?;
                } else {
                    return Err(TelegramDeliveryError::General(format!(
                        "Joined required channel, but bot @{bot_username}'s gate message did not include a 'Try Again' button or start link to re-request the file."
                    )));
                }

                // Refresh wait budget so the bot has time to send the media file after retry
                step_start = Instant::now();
                step_timeout = Duration::from_secs(RETRY_MEDIA_WAIT_SECS);
            } else if let Some(reason) = detect_unavailable_file_message(&newest_msg.text) {
                log::warn!(
                    "Bot @{} reported file unavailable (msg {}): {}",
                    bot_username,
                    newest_msg.id,
                    reason
                );
                return Err(TelegramDeliveryError::FileUnavailable(format!(
                    "File unavailable from @{bot_username}: \"{reason}\". Please choose another release or search again."
                )));
            }
        }
    }

    if gate_attempts > 0 {
        let alert_suffix = last_callback_alert
            .as_deref()
            .map(|a| format!(" Bot replied: {a}"))
            .unwrap_or_default();
        Err(TelegramDeliveryError::General(format!(
            "Joined required channel and retried with @{bot_username}, but no media file arrived.{alert_suffix} Please verify membership in Telegram and try again."
        )))
    } else {
        Err(TelegramDeliveryError::Timeout(
            bot_username.to_string(),
            INITIAL_MEDIA_WAIT_SECS,
        ))
    }
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

    /// Attempts to join a Telegram channel (public @username or private invite link)
    /// using the authenticated user's MTProto session.
    /// Strictly rejects non-Telegram links as a security safeguard.
    pub async fn join_channel_from_url(&self, url: &str) -> Result<JoinChannelOutcome, String> {
        let target = parse_channel_link(url)
            .ok_or_else(|| format!("Invalid or non-Telegram channel link: '{url}'. Only authentic Telegram links can be joined."))?;

        let status = self.auth_service.get_status().await.map_err(|e| e.to_string())?;
        if !status.connected {
            return Err("Telegram client is not connected.".to_string());
        }

        match self.auth_service.backend().as_ref() {
            TelegramBackendKind::Mock(_) => {
                // In mock mode, return successful simulated join outcome based on URL contents
                match target {
                    ParsedChannelTarget::Public(u) => {
                        if u.contains("flood") {
                            Err("Telegram rate limit: FLOOD_WAIT_30. Please wait before joining more channels.".to_string())
                        } else if u.contains("fail") || u.contains("invalid") {
                            Err(format!("Mock failure joining public channel @{u}"))
                        } else if u.contains("request") {
                            Ok(JoinChannelOutcome::RequestSent)
                        } else if u.contains("already") {
                            Ok(JoinChannelOutcome::AlreadyParticipant)
                        } else {
                            Ok(JoinChannelOutcome::JoinedPublic(u))
                        }
                    }
                    ParsedChannelTarget::Private(h) => {
                        if h.contains("flood") {
                            Err("Telegram rate limit: FLOOD_WAIT_30. Please wait before joining more channels.".to_string())
                        } else if h.contains("fail") || h.contains("expired") {
                            Err(format!("Mock failure joining private channel '{h}'"))
                        } else if h.contains("request") {
                            Ok(JoinChannelOutcome::RequestSent)
                        } else if h.contains("already") {
                            Ok(JoinChannelOutcome::AlreadyParticipant)
                        } else {
                            Ok(JoinChannelOutcome::JoinedPrivate(h))
                        }
                    }
                }
            }
            TelegramBackendKind::Mtproto(mtproto) => {
                let client = mtproto.get_client().await.map_err(|e| e.to_string())?;
                if !client.is_authorized().await.unwrap_or(false) {
                    return Err("Telegram user client is not authenticated.".to_string());
                }

                match target {
                    ParsedChannelTarget::Private(hash) => {
                        log::info!("Attempting to import chat invite hash: '{hash}'");
                        let import_req = grammers_tl_types::functions::messages::ImportChatInvite {
                            hash: hash.clone(),
                        };
                        match client.invoke(&import_req).await {
                            Ok(_) => {
                                log::info!("Successfully joined private channel via invite hash '{hash}'");
                                Ok(JoinChannelOutcome::JoinedPrivate(hash))
                            }
                            Err(e) => {
                                let err_str = e.to_string();
                                if err_str.contains("USER_ALREADY_PARTICIPANT") {
                                    log::info!("Account is already a participant of private channel '{hash}'");
                                    Ok(JoinChannelOutcome::AlreadyParticipant)
                                } else if err_str.contains("INVITE_REQUEST_SENT") {
                                    log::info!("Join request sent for private channel '{hash}' (admin approval required)");
                                    Ok(JoinChannelOutcome::RequestSent)
                                } else if err_str.contains("FLOOD_WAIT") {
                                    Err(format!("Telegram rate limit: {err_str}. Please wait before joining more channels."))
                                } else if err_str.contains("INVITE_HASH_EXPIRED") {
                                    Err(format!("The private invite link for '{hash}' has expired."))
                                } else {
                                    Err(format!("Failed to join private channel: {err_str}"))
                                }
                            }
                        }
                    }
                    ParsedChannelTarget::Public(username) => {
                        log::info!("Resolving and joining public channel: '@{username}'");
                        let resolved = client
                            .invoke(&grammers_tl_types::functions::contacts::ResolveUsername {
                                username: username.clone(),
                                referer: None,
                            })
                            .await
                            .map_err(|e| format!("Failed to resolve channel @{username}: {e}"))?;

                        let input_channel = match resolved {
                            grammers_tl_types::enums::contacts::ResolvedPeer::Peer(p) => match p.peer {
                                grammers_tl_types::enums::Peer::Channel(c) => {
                                    let access_hash = p.chats.iter().find_map(|chat| {
                                        if let grammers_tl_types::enums::Chat::Channel(real_ch) = chat {
                                            if real_ch.id == c.channel_id {
                                                return real_ch.access_hash;
                                            }
                                        }
                                        None
                                    }).unwrap_or(0);

                                    grammers_tl_types::enums::InputChannel::Channel(grammers_tl_types::types::InputChannel {
                                        channel_id: c.channel_id,
                                        access_hash,
                                    })
                                }
                                _ => return Err(format!("Peer @{username} is a user or chat, not a channel.")),
                            },
                        };

                        let join_req = grammers_tl_types::functions::channels::JoinChannel {
                            channel: input_channel,
                        };
                        match client.invoke(&join_req).await {
                            Ok(_) => {
                                log::info!("Successfully joined public channel '@{username}'");
                                Ok(JoinChannelOutcome::JoinedPublic(username))
                            }
                            Err(e) => {
                                let err_str = e.to_string();
                                if err_str.contains("USER_ALREADY_PARTICIPANT") {
                                    log::info!("Account is already a participant of public channel '@{username}'");
                                    Ok(JoinChannelOutcome::AlreadyParticipant)
                                } else if err_str.contains("INVITE_REQUEST_SENT") {
                                    log::info!("Join request sent for public channel '@{username}' (admin approval required)");
                                    Ok(JoinChannelOutcome::RequestSent)
                                } else if err_str.contains("FLOOD_WAIT") {
                                    Err(format!("Telegram rate limit: {err_str}. Please wait before joining more channels."))
                                } else if err_str.contains("CHANNEL_PRIVATE") {
                                    Err(format!("Channel @{username} is private and requires an invite link."))
                                } else {
                                    Err(format!("Failed to join public channel @{username}: {err_str}"))
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    async fn join_channel_structured(
        &self,
        url: &str,
    ) -> Result<JoinChannelOutcome, TelegramDeliveryError> {
        match self.join_channel_from_url(url).await {
            Ok(outcome) => Ok(outcome),
            Err(err) => {
                if let Some(secs) = extract_flood_wait_seconds(&err) {
                    Err(TelegramDeliveryError::RateLimited(secs))
                } else {
                    Err(TelegramDeliveryError::General(err))
                }
            }
        }
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
        if lower_id.contains("unavailable") {
            let bot = request.source_bot.as_deref().unwrap_or("Spoty_xbot");
            return Err(TelegramDeliveryError::FileUnavailable(format!(
                "File unavailable from @{bot}: \"File is unavailable, sorry. Search again.\". Please choose another release or search again."
            )));
        }
        if lower_id.contains("rate_limit") {
            return Err(TelegramDeliveryError::RateLimited(30));
        }
        if lower_id.contains("fsub_locked") {
            return Err(TelegramDeliveryError::ChannelRequirement(ChannelRequirement {
                required: true,
                channel_title: Some("Cineforge Updates Channel".to_string()),
                channel_username: Some("cineforge_updates".to_string()),
                invite_url: Some("https://t.me/cineforge_updates".to_string()),
                channel_urls: vec!["https://t.me/cineforge_updates".to_string()],
                message: "You must join this channel before accessing media files.".to_string(),
                retry_callback: Some("retry_fsub_mock".to_string()),
                retry_start_payload: None,
            }));
        }
        if lower_id.contains("fsub") {
            let target_url = if let Some(ref explicit) = request.auto_join_channel {
                explicit.as_str()
            } else if lower_id.contains("fsub_fail") {
                "https://t.me/fail_channel"
            } else if lower_id.contains("fsub_request") {
                "https://t.me/+request_only_hash"
            } else if lower_id.contains("fsub_flood") {
                "https://t.me/flood_channel"
            } else if lower_id.contains("fsub_invalid") {
                "https://evil-phishing.example/+hash"
            } else {
                "https://t.me/cineforge_updates"
            };

            match self.join_channel_structured(target_url).await? {
                JoinChannelOutcome::RequestSent => {
                    return Err(TelegramDeliveryError::General(format!(
                        "Join request sent for '{target_url}'. Admin approval is required before media can be delivered."
                    )));
                }
                JoinChannelOutcome::JoinedPublic(_)
                | JoinChannelOutcome::JoinedPrivate(_)
                | JoinChannelOutcome::AlreadyParticipant => {}
            }
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

        // Ensure personal bot token is available and active in Go streamer sidecar before forwarding media
        let runtime_token = self
            .provisioning_service
            .get_runtime_token()
            .await
            .filter(|t| !t.trim().is_empty())
            .ok_or_else(|| {
                TelegramDeliveryError::General(
                    "Personal streamer bot token is unavailable. Please reconnect Telegram or re-provision your streamer bot."
                        .to_string(),
                )
            })?;
        let _ = self
            .sidecar_service
            .start_with_token(Some(runtime_token.as_str()))
            .await
            .map_err(|e| {
                TelegramDeliveryError::General(format!("Failed to start local Go streamer sidecar: {e}"))
            })?;

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

        // 2. Trigger delivery, resolve any FSub gates automatically, and wait for genuine media
        struct MtprotoDeliverySession<'a> {
            service: &'a TelegramDeliveryService,
            client: &'a grammers_client::Client,
            bot_peer: grammers_tl_types::enums::InputPeer,
            bot_username: String,
        }

        impl<'a> BotDeliverySession for MtprotoDeliverySession<'a> {
            async fn send_start(&mut self, payload: &str) -> Result<(), TelegramDeliveryError> {
                let start_cmd = format!("/start {payload}");
                let random_id = {
                    use std::time::SystemTime;
                    SystemTime::now()
                        .duration_since(SystemTime::UNIX_EPOCH)
                        .unwrap()
                        .as_nanos() as i64
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
                    peer: self.bot_peer.clone(),
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

                self.client.invoke(&send_req).await.map_err(|e| {
                    let err_str = e.to_string();
                    if let Some(secs) = extract_flood_wait_seconds(&err_str) {
                        TelegramDeliveryError::RateLimited(secs)
                    } else {
                        TelegramDeliveryError::General(format!(
                            "Failed to send /start command to @{}: {err_str}",
                            self.bot_username
                        ))
                    }
                })?;
                Ok(())
            }

            async fn click_callback(
                &mut self,
                msg_id: i32,
                data: &str,
            ) -> Result<Option<String>, TelegramDeliveryError> {
                let cb_req = grammers_tl_types::functions::messages::GetBotCallbackAnswer {
                    game: false,
                    peer: self.bot_peer.clone(),
                    msg_id,
                    data: Some(data.as_bytes().to_vec()),
                    password: None,
                };

                match self.client.invoke(&cb_req).await {
                    Ok(grammers_tl_types::enums::messages::BotCallbackAnswer::Answer(ans)) => {
                        Ok(ans.message)
                    }
                    Err(e) => {
                        let err_str = e.to_string();
                        if let Some(secs) = extract_flood_wait_seconds(&err_str) {
                            Err(TelegramDeliveryError::RateLimited(secs))
                        } else if err_str.contains("BOT_RESPONSE_TIMEOUT") {
                            Ok(None)
                        } else {
                            Err(TelegramDeliveryError::General(format!(
                                "Failed to activate callback button on @{}: {err_str}",
                                self.bot_username
                            )))
                        }
                    }
                }
            }

            async fn get_recent_messages(
                &mut self,
                limit: i32,
            ) -> Result<Vec<BotChatMessage>, TelegramDeliveryError> {
                let hist_req = grammers_tl_types::functions::messages::GetHistory {
                    peer: self.bot_peer.clone(),
                    offset_id: 0,
                    offset_date: 0,
                    add_offset: 0,
                    limit,
                    max_id: 0,
                    min_id: 0,
                    hash: 0,
                };

                let hist = self.client.invoke(&hist_req).await.map_err(|e| {
                    TelegramDeliveryError::General(format!(
                        "Failed to read messages from @{}: {e}",
                        self.bot_username
                    ))
                })?;

                let raw_msgs = match hist {
                    grammers_tl_types::enums::messages::Messages::Messages(m) => m.messages,
                    grammers_tl_types::enums::messages::Messages::Slice(s) => s.messages,
                    grammers_tl_types::enums::messages::Messages::ChannelMessages(c) => c.messages,
                    grammers_tl_types::enums::messages::Messages::NotModified(_) => vec![],
                };

                Ok(raw_msgs
                    .iter()
                    .filter_map(extract_bot_chat_message)
                    .collect())
            }

            async fn join_channel(
                &mut self,
                url: &str,
            ) -> Result<JoinChannelOutcome, TelegramDeliveryError> {
                self.service.join_channel_structured(url).await
            }

            async fn sleep_ms(&mut self, ms: u64) {
                tokio::time::sleep(Duration::from_millis(ms)).await;
            }
        }

        let mut session = MtprotoDeliverySession {
            service: self,
            client: &client,
            bot_peer: bot_peer.clone(),
            bot_username: bot_username.clone(),
        };

        let captured = resolve_and_capture_media(&mut session, request, &bot_username).await?;
        let doc_msg_id = captured.msg_id;
        let file_name = captured.file_name;
        let mime_type = captured.mime_type;
        let file_size = captured.file_size;

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

        // Capture baseline message ID with personal streamer bot before forwarding
        let baseline_streamer_msg_id: i32 = match client
            .invoke(&grammers_tl_types::functions::messages::GetHistory {
                peer: streamer_peer.clone(),
                offset_id: 0,
                offset_date: 0,
                add_offset: 0,
                limit: 1,
                max_id: 0,
                min_id: 0,
                hash: 0,
            })
            .await
        {
            Ok(hist) => {
                let raw = match hist {
                    grammers_tl_types::enums::messages::Messages::Messages(m) => m.messages,
                    grammers_tl_types::enums::messages::Messages::Slice(s) => s.messages,
                    grammers_tl_types::enums::messages::Messages::ChannelMessages(c) => c.messages,
                    grammers_tl_types::enums::messages::Messages::NotModified(_) => vec![],
                };
                raw.iter()
                    .filter_map(extract_bot_chat_message)
                    .map(|m| m.id)
                    .max()
                    .unwrap_or(0)
            }
            Err(_) => 0,
        };

        // 5. Forward captured media document to personal streamer bot
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
            id: vec![doc_msg_id],
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

        // 6. Poll streamer bot for the newly generated stream link
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
                limit: 5,
                max_id: 0,
                min_id: baseline_streamer_msg_id,
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
                        if !msg.out && msg.id > baseline_streamer_msg_id {
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

        let (channel_msg_id, hash) = match (stream_msg_id, stream_hash) {
            (Some(id), Some(h)) => (id, h),
            _ => {
                return Err(TelegramDeliveryError::General(format!(
                    "Forwarded media file to personal streamer bot @{streamer_username}, but it did not return a playback link in time."
                )));
            }
        };

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
            auto_join_channel: None,
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
            auto_join_channel: None,
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
            auto_join_channel: None,
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
            auto_join_channel: None,
        };

        let res = delivery.deliver_candidate(&req, 8080).await;
        assert!(matches!(res, Err(TelegramDeliveryError::Timeout(_, _))));
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_fsub_auto_resolves_without_popup() {
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
            candidate_id: "cand_fsub_auto_test".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(104),
            candidate_title: Some("Inception (2010)".to_string()),
            start_payload: None,
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let res = delivery
            .deliver_candidate(&req, 8080)
            .await
            .expect("FSub gate should auto-join valid channel and deliver stream");
        assert!(res.success);
        assert!(res.stream_url.contains("/api/stream/"));
    }

    #[tokio::test]
    async fn test_deliver_candidate_mock_fsub_errors() {
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

        let base_req = |id: &str| CandidateDeliveryRequest {
            candidate_id: id.to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(104),
            candidate_title: Some("Test".to_string()),
            start_payload: None,
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        // 1. Admin approval required -> clear General error
        let res_req = delivery.deliver_candidate(&base_req("cand_fsub_request"), 8080).await;
        match res_req {
            Err(TelegramDeliveryError::General(msg)) => {
                assert!(msg.contains("Admin approval is required"));
            }
            other => panic!("Expected admin approval error, got {:?}", other),
        }

        // 2. FloodWait -> RateLimited(30)
        let res_flood = delivery.deliver_candidate(&base_req("cand_fsub_flood"), 8080).await;
        assert!(matches!(res_flood, Err(TelegramDeliveryError::RateLimited(30))));

        // 3. Non-Telegram link -> General rejection error
        let res_invalid = delivery.deliver_candidate(&base_req("cand_fsub_invalid"), 8080).await;
        match res_invalid {
            Err(TelegramDeliveryError::General(msg)) => {
                assert!(msg.contains("Only authentic Telegram links can be joined"));
            }
            other => panic!("Expected non-Telegram rejection error, got {:?}", other),
        }
    }

    #[tokio::test]
    async fn test_join_channel_from_url_outcomes() {
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

        // 1. Public channel join
        let res1 = delivery.join_channel_from_url("https://t.me/cineforge_updates").await;
        assert_eq!(res1, Ok(JoinChannelOutcome::JoinedPublic("cineforge_updates".to_string())));

        // 2. Private channel invite join
        let res2 = delivery.join_channel_from_url("https://t.me/+AbCdEfGh12345").await;
        assert_eq!(res2, Ok(JoinChannelOutcome::JoinedPrivate("AbCdEfGh12345".to_string())));

        // 3. Already a member
        let res3 = delivery.join_channel_from_url("https://t.me/already_joined_channel").await;
        assert_eq!(res3, Ok(JoinChannelOutcome::AlreadyParticipant));

        // 4. Request sent (admin approval needed)
        let res4 = delivery.join_channel_from_url("https://t.me/+request_only_hash").await;
        assert_eq!(res4, Ok(JoinChannelOutcome::RequestSent));

        // 5. Non-telegram link rejection (safeguard)
        let res5 = delivery.join_channel_from_url("https://malicious.com/+hash").await;
        assert!(res5.is_err());
        assert!(res5.unwrap_err().contains("Only authentic Telegram links can be joined"));

        // 6. Explicit failure
        let res6 = delivery.join_channel_from_url("https://t.me/fail_channel").await;
        assert!(res6.is_err());
    }

    /// Scriptable mock BotDeliverySession to test the complete FSub state machine:
    /// trigger -> gate reply -> channel join -> 2.5s sync -> retry callback / /start link -> media capture.
    struct ScriptedBotSession {
        messages: Vec<BotChatMessage>,
        actions: Vec<String>,
        joined_urls: Vec<String>,
        sleeps_ms: Vec<u64>,
        next_msg_id: i32,
        on_start: Box<dyn FnMut(&str, &mut Vec<BotChatMessage>, &mut i32) + Send>,
        on_callback: Box<dyn FnMut(i32, &str, &mut Vec<BotChatMessage>, &mut i32) -> Result<Option<String>, TelegramDeliveryError> + Send>,
        on_join: Box<dyn FnMut(&str) -> Result<JoinChannelOutcome, TelegramDeliveryError> + Send>,
    }

    impl ScriptedBotSession {
        fn new() -> Self {
            Self {
                messages: Vec::new(),
                actions: Vec::new(),
                joined_urls: Vec::new(),
                sleeps_ms: Vec::new(),
                next_msg_id: 500,
                on_start: Box::new(|_, _, _| {}),
                on_callback: Box::new(|_, _, _, _| Ok(None)),
                on_join: Box::new(|url| {
                    let target = parse_channel_link(url).ok_or_else(|| {
                        TelegramDeliveryError::General(format!("Invalid channel link: {url}"))
                    })?;
                    match target {
                        ParsedChannelTarget::Public(u) => {
                            if u.contains("already") {
                                Ok(JoinChannelOutcome::AlreadyParticipant)
                            } else if u.contains("request") {
                                Ok(JoinChannelOutcome::RequestSent)
                            } else if u.contains("flood") {
                                Err(TelegramDeliveryError::RateLimited(45))
                            } else {
                                Ok(JoinChannelOutcome::JoinedPublic(u))
                            }
                        }
                        ParsedChannelTarget::Private(h) => {
                            if h.contains("request") {
                                Ok(JoinChannelOutcome::RequestSent)
                            } else if h.contains("flood") {
                                Err(TelegramDeliveryError::RateLimited(45))
                            } else {
                                Ok(JoinChannelOutcome::JoinedPrivate(h))
                            }
                        }
                    }
                }),
            }
        }
    }

    impl BotDeliverySession for ScriptedBotSession {
        async fn send_start(&mut self, payload: &str) -> Result<(), TelegramDeliveryError> {
            self.actions.push(format!("start:{payload}"));
            (self.on_start)(payload, &mut self.messages, &mut self.next_msg_id);
            Ok(())
        }

        async fn click_callback(
            &mut self,
            msg_id: i32,
            data: &str,
        ) -> Result<Option<String>, TelegramDeliveryError> {
            self.actions.push(format!("callback:{msg_id}:{data}"));
            (self.on_callback)(msg_id, data, &mut self.messages, &mut self.next_msg_id)
        }

        async fn get_recent_messages(
            &mut self,
            limit: i32,
        ) -> Result<Vec<BotChatMessage>, TelegramDeliveryError> {
            let take_n = limit.max(1) as usize;
            let mut recent: Vec<BotChatMessage> =
                self.messages.iter().rev().take(take_n).cloned().collect();
            // Match Telegram GetHistory order (newest first)
            Ok(recent.drain(..).collect())
        }

        async fn join_channel(
            &mut self,
            url: &str,
        ) -> Result<JoinChannelOutcome, TelegramDeliveryError> {
            self.actions.push(format!("join:{url}"));
            self.joined_urls.push(url.to_string());
            (self.on_join)(url)
        }

        async fn sleep_ms(&mut self, ms: u64) {
            self.sleeps_ms.push(ms);
        }
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_retry_callback_then_captures_media() {
        let mut session = ScriptedBotSession::new();
        session.messages.push(BotChatMessage {
            id: 100,
            out: false,
            edit_date: None,
            text: "Select quality:".to_string(),
            buttons: vec![],
            media_doc: None,
        });

        session.on_start = Box::new(|payload, msgs, next_id| {
            if payload == "get_inception" {
                let id = *next_id;
                *next_id += 1;
                msgs.push(BotChatMessage {
                    id,
                    out: false,
                    edit_date: None,
                    text: "⚠️ You must join our Updates Channel first!".to_string(),
                    buttons: vec![
                        RawInlineButton {
                            text: "📢 Join Channel".to_string(),
                            callback_data: None,
                            url: Some("https://t.me/+SecretInviteHash".to_string()),
                        },
                        RawInlineButton {
                            text: "🔄 Try Again".to_string(),
                            callback_data: Some("verify_fsub_99".to_string()),
                            url: None,
                        },
                    ],
                    media_doc: None,
                });
            }
        });

        session.on_callback = Box::new(|gate_id, data, msgs, next_id| {
            assert_eq!(data, "verify_fsub_99");
            assert_eq!(gate_id, 500);
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "Here is your movie!".to_string(),
                buttons: vec![],
                media_doc: Some(BotMediaDoc {
                    file_name: "Inception.2010.1080p.mp4".to_string(),
                    mime_type: "video/mp4".to_string(),
                    file_size: 2_100_000_000,
                    is_sticker: false,
                }),
            });
            Ok(Some("Verified!".to_string()))
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-123".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(100),
            candidate_title: Some("Inception (2010)".to_string()),
            start_payload: Some("get_inception".to_string()),
            callback_data: None,
            quality: Some("1080P".to_string()),
            auto_join_channel: None,
        };

        let captured = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect("Retry callback flow should resolve gate and capture video");

        assert_eq!(captured.msg_id, 501);
        assert_eq!(captured.file_name, "Inception.2010.1080p.mp4");
        assert_eq!(session.joined_urls, vec!["https://t.me/+SecretInviteHash".to_string()]);
        assert!(session.sleeps_ms.contains(&2500));
        assert_eq!(
            session.actions,
            vec![
                "start:get_inception".to_string(),
                "join:https://t.me/+SecretInviteHash".to_string(),
                "callback:500:verify_fsub_99".to_string(),
            ]
        );
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_start_link_then_captures_media() {
        let mut session = ScriptedBotSession::new();
        session.messages.push(BotChatMessage {
            id: 200,
            out: false,
            edit_date: None,
            text: "Movie list".to_string(),
            buttons: vec![],
            media_doc: None,
        });

        session.on_callback = Box::new(|msg_id, cb, msgs, next_id| {
            if msg_id == 200 && cb == "dl_interstellar" {
                let id = *next_id;
                *next_id += 1;
                msgs.push(BotChatMessage {
                    id,
                    out: false,
                    edit_date: None,
                    text: "Please join @cineforge_updates to unlock this file.".to_string(),
                    buttons: vec![
                        RawInlineButton {
                            text: "📢 Updates Channel".to_string(),
                            callback_data: None,
                            url: Some("https://t.me/cineforge_updates".to_string()),
                        },
                        RawInlineButton {
                            text: "✅ Try Again".to_string(),
                            callback_data: None,
                            url: Some("https://t.me/Spoty_xbot?start=retry_interstellar_77".to_string()),
                        },
                    ],
                    media_doc: None,
                });
            }
            Ok(None)
        });

        session.on_start = Box::new(|payload, msgs, next_id| {
            assert_eq!(payload, "retry_interstellar_77");
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "".to_string(),
                buttons: vec![],
                media_doc: Some(BotMediaDoc {
                    file_name: "Interstellar.2014.4K.mkv".to_string(),
                    mime_type: "video/x-matroska".to_string(),
                    file_size: 4_500_000_000,
                    is_sticker: false,
                }),
            });
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-456".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: Some(200),
            candidate_title: Some("Interstellar (2014)".to_string()),
            start_payload: None,
            callback_data: Some("dl_interstellar".to_string()),
            quality: Some("4K".to_string()),
            auto_join_channel: None,
        };

        let captured = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect("Start link flow should resolve gate and capture video");

        assert_eq!(captured.msg_id, 501);
        assert_eq!(captured.file_name, "Interstellar.2014.4K.mkv");
        assert_eq!(session.joined_urls, vec!["https://t.me/cineforge_updates".to_string()]);
        assert!(session.sleeps_ms.contains(&2500));
        assert_eq!(
            session.actions,
            vec![
                "callback:200:dl_interstellar".to_string(),
                "join:https://t.me/cineforge_updates".to_string(),
                "start:retry_interstellar_77".to_string(),
            ]
        );
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_never_treats_gate_sticker_as_video() {
        let mut session = ScriptedBotSession::new();
        session.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            // Gate message includes a sticker/thumbnail document — must NOT be mistaken for video!
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "Must join @already_member_ch first!".to_string(),
                buttons: vec![RawInlineButton {
                    text: "Try Again".to_string(),
                    callback_data: Some("cb_try".to_string()),
                    url: None,
                }],
                media_doc: Some(BotMediaDoc {
                    file_name: "AnimatedSticker.tgs".to_string(),
                    mime_type: "application/x-tgsticker".to_string(),
                    file_size: 12_000,
                    is_sticker: true,
                }),
            });
        });

        session.on_callback = Box::new(|_, _, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "".to_string(),
                buttons: vec![],
                media_doc: Some(BotMediaDoc {
                    file_name: "RealMovie.mp4".to_string(),
                    mime_type: "video/mp4".to_string(),
                    file_size: 900_000_000,
                    is_sticker: false,
                }),
            });
            Ok(None)
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-789".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: None,
            candidate_title: Some("Movie".to_string()),
            start_payload: Some("get_movie".to_string()),
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let captured = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect("Should skip sticker on gate message and capture actual video");
        assert_eq!(captured.msg_id, 501);
        assert_eq!(captured.file_name, "RealMovie.mp4");
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_bounded_retries_and_multi_channel() {
        let mut session = ScriptedBotSession::new();
        session.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "Join both channels!".to_string(),
                buttons: vec![
                    RawInlineButton {
                        text: "Channel 1".to_string(),
                        callback_data: None,
                        url: Some("https://t.me/ch_one".to_string()),
                    },
                    RawInlineButton {
                        text: "Channel 2".to_string(),
                        callback_data: None,
                        url: Some("https://t.me/+ch_two".to_string()),
                    },
                    RawInlineButton {
                        text: "Try Again".to_string(),
                        callback_data: Some("try_1".to_string()),
                        url: None,
                    },
                ],
                media_doc: None,
            });
        });

        // Every retry returns another distinct gate message -> must stop cleanly after MAX_GATE_RETRIES (2)
        session.on_callback = Box::new(|_, _, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: format!("Still must join channel #{id}"),
                buttons: vec![
                    RawInlineButton {
                        text: "Another Channel".to_string(),
                        callback_data: None,
                        url: Some(format!("https://t.me/extra_ch_{id}")),
                    },
                    RawInlineButton {
                        text: "Try Again".to_string(),
                        callback_data: Some(format!("try_{id}")),
                        url: None,
                    },
                ],
                media_doc: None,
            });
            Ok(Some("Membership check incomplete".to_string()))
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-bound".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: None,
            candidate_title: Some("Movie".to_string()),
            start_payload: Some("get_bound".to_string()),
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let err = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect_err("Should stop after bounded 2 gate retries");

        let msg = err.to_string();
        assert!(msg.contains("2 automatic join attempts"));
        assert!(msg.contains("Membership check incomplete"));
        // Joined both channels from gate 1 + 1 channel from gate 2 = 3 joins total, then stopped at gate 3
        assert_eq!(session.joined_urls.len(), 3);
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_rejects_non_telegram_only_link() {
        let mut session = ScriptedBotSession::new();
        session.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "You must join our updates channel to continue.".to_string(),
                buttons: vec![RawInlineButton {
                    text: "Join External".to_string(),
                    callback_data: None,
                    url: Some("https://phishing.example.com/+badhash".to_string()),
                }],
                media_doc: None,
            });
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-sec".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: None,
            candidate_title: Some("Movie".to_string()),
            start_payload: Some("get_sec".to_string()),
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let err = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect_err("Non-Telegram channel link must be rejected");
        assert!(err.to_string().contains("no valid Telegram channel"));
        assert!(session.joined_urls.is_empty());
    }

    #[tokio::test]
    async fn test_resolve_fsub_gate_admin_approval_and_flood_wait() {
        // Admin approval required
        let mut session_req = ScriptedBotSession::new();
        session_req.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "Join private channel!".to_string(),
                buttons: vec![
                    RawInlineButton {
                        text: "Join".to_string(),
                        callback_data: None,
                        url: Some("https://t.me/+request_approval_hash".to_string()),
                    },
                    RawInlineButton {
                        text: "Try Again".to_string(),
                        callback_data: Some("try_cb".to_string()),
                        url: None,
                    },
                ],
                media_doc: None,
            });
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-req".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: None,
            candidate_title: Some("Movie".to_string()),
            start_payload: Some("get_req".to_string()),
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let err_req = resolve_and_capture_media(&mut session_req, &req, "Spoty_xbot")
            .await
            .expect_err("Admin approval pending should return descriptive error");
        assert!(err_req.to_string().contains("Admin approval is required"));
        assert!(!session_req.actions.iter().any(|a| a.starts_with("callback:")));

        // Flood limit
        let mut session_flood = ScriptedBotSession::new();
        session_flood.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "Join channel!".to_string(),
                buttons: vec![RawInlineButton {
                    text: "Join".to_string(),
                    callback_data: None,
                    url: Some("https://t.me/flood_limit_channel".to_string()),
                }],
                media_doc: None,
            });
        });

        let err_flood = resolve_and_capture_media(&mut session_flood, &req, "Spoty_xbot")
            .await
            .expect_err("FloodWait should map to RateLimited");
        assert!(matches!(err_flood, TelegramDeliveryError::RateLimited(45)));
    }

    #[tokio::test]
    async fn test_resolve_file_unavailable_stops_immediately_without_fsub_or_media() {
        let mut session = ScriptedBotSession::new();
        session.on_start = Box::new(|_, msgs, next_id| {
            let id = *next_id;
            *next_id += 1;
            msgs.push(BotChatMessage {
                id,
                out: false,
                edit_date: None,
                text: "File is unavailable, sorry. Search again.".to_string(),
                buttons: vec![],
                media_doc: None,
            });
        });

        let req = CandidateDeliveryRequest {
            candidate_id: "cand-unavail".to_string(),
            source_bot: Some("Spoty_xbot".to_string()),
            source_message_id: None,
            candidate_title: Some("Missing Movie".to_string()),
            start_payload: Some("get_missing".to_string()),
            callback_data: None,
            quality: None,
            auto_join_channel: None,
        };

        let err = resolve_and_capture_media(&mut session, &req, "Spoty_xbot")
            .await
            .expect_err("Unavailable file reply should return FileUnavailable immediately");

        assert!(matches!(err, TelegramDeliveryError::FileUnavailable(_)));
        assert!(err.to_string().contains("File is unavailable, sorry. Search again."));
        assert!(session.joined_urls.is_empty());
        // Must stop on first poll where message appeared rather than polling 65 iterations
        assert_eq!(session.sleeps_ms, vec![800]);
    }
}
