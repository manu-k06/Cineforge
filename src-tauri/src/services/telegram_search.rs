use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;

use crate::models::search::{
    ChannelRequirement, SearchPaginationInfo, SearchResponse,
    SearchSuggestionItem, SearchSuggestionsResponse, SelectedResultRequest, SelectedResultResponse,
};
use crate::services::telegram_auth::{TelegramAuthService, TelegramBackendKind};
use crate::services::telegram_search_parser::{
    parse_bot_response, parse_deep_link, RawBotMessage, RawInlineButton,
};

#[derive(Debug, Error)]
pub enum TelegramSearchError {
    #[error("Your Telegram account is not connected. Please connect your account in settings to search for cinema.")]
    NotConnected,
    #[error("Telegram bot @{0} did not respond within {1} seconds. The bot may be busy or experiencing downtime.")]
    Timeout(String, u64),
    #[error("Telegram rate limit reached. Please wait {0} seconds before making another search request.")]
    RateLimited(u64),
    #[error("Search failed: {0}")]
    General(String),
}

/// Unified Telegram Search Service reusing the authenticated user's session.
pub struct TelegramSearchService {
    auth_service: Arc<TelegramAuthService>,
    default_bot_username: String,
}

impl TelegramSearchService {
    pub fn new(auth_service: Arc<TelegramAuthService>) -> Self {
        let default_bot_username = std::env::var("TELEGRAM_BOT_USERNAME")
            .or_else(|_| std::env::var("CINEFORGE_TELEGRAM_BOT_USERNAME"))
            .unwrap_or_else(|_| "Spoty_xbot".to_string())
            .trim_start_matches('@')
            .to_string();

        Self {
            auth_service,
            default_bot_username,
        }
    }

    pub fn default_bot_username(&self) -> &str {
        &self.default_bot_username
    }

    /// Primary search executor: sends query to the configured bot and parses candidates.
    pub async fn search_movies(
        &self,
        query: &str,
        page: i64,
        max_pages: i64,
    ) -> Result<SearchResponse, TelegramSearchError> {
        let clean_query = query.trim();
        if clean_query.is_empty() {
            return Ok(SearchResponse {
                query: "".to_string(),
                candidates: Vec::new(),
                title_groups: HashMap::new(),
                pagination: Some(SearchPaginationInfo::default()),
                channel_requirement: None,
                metadata_enrichment: HashMap::new(),
                is_cached: false,
                error: None,
            });
        }

        // 1. Check account connection status
        let status = self.auth_service.get_status().await.map_err(TelegramSearchError::General)?;
        if !status.connected {
            return Err(TelegramSearchError::NotConnected);
        }

        // 2. Dispatch to underlying backend
        match self.auth_service.backend().as_ref() {
            TelegramBackendKind::Mock(mock) => {
                self.mock_search_movies(mock, clean_query, page, max_pages).await
            }
            TelegramBackendKind::Mtproto(mtproto) => {
                self.mtproto_search_movies(mtproto, clean_query, page, max_pages).await
            }
        }
    }

    /// Resolves and validates a selected candidate for upcoming delivery.
    pub async fn select_candidate(
        &self,
        request: &SelectedResultRequest,
    ) -> Result<SelectedResultResponse, TelegramSearchError> {
        let status = self.auth_service.get_status().await.map_err(TelegramSearchError::General)?;
        if !status.connected {
            return Err(TelegramSearchError::NotConnected);
        }

        let target_bot = request
            .source_bot
            .clone()
            .unwrap_or_else(|| self.default_bot_username.clone());

        // Validate selection type
        if let Some(ref payload) = request.start_payload {
            let details = serde_json::json!({
                "bot_username": target_bot,
                "start_payload": payload,
                "command": format!("/start {}", payload),
                "source_message_id": request.source_message_id,
            });

            return Ok(SelectedResultResponse {
                status: "resolved".to_string(),
                resolved_type: "telegram_deep_link".to_string(),
                target_bot: target_bot.clone(),
                action_summary: format!("Resolved Telegram deep link for delivery bot @{target_bot}"),
                details,
                channel_requirement: None,
            });
        }

        if let Some(ref cb_data) = request.callback_data {
            let details = serde_json::json!({
                "source_bot": target_bot,
                "callback_data": cb_data,
                "source_message_id": request.source_message_id,
            });

            return Ok(SelectedResultResponse {
                status: "resolved".to_string(),
                resolved_type: "callback".to_string(),
                target_bot: target_bot.clone(),
                action_summary: format!("Resolved inline button callback action for bot @{target_bot}"),
                details,
                channel_requirement: None,
            });
        }

        if let Some(ref url) = request.source_url {
            if let Some((b, p)) = parse_deep_link(url) {
                let effective_bot = if b.is_empty() { target_bot } else { b };
                let details = serde_json::json!({
                    "bot_username": effective_bot,
                    "start_payload": p,
                    "source_url": url,
                    "command": format!("/start {}", p),
                });
                return Ok(SelectedResultResponse {
                    status: "resolved".to_string(),
                    resolved_type: "telegram_deep_link".to_string(),
                    target_bot: effective_bot,
                    action_summary: format!("Resolved Telegram deep link from URL for bot"),
                    details,
                    channel_requirement: None,
                });
            }

            let details = serde_json::json!({ "source_url": url });
            return Ok(SelectedResultResponse {
                status: "resolved".to_string(),
                resolved_type: "url".to_string(),
                target_bot,
                action_summary: format!("External URL reference: {url}"),
                details,
                channel_requirement: None,
            });
        }

        Err(TelegramSearchError::General(
            "Invalid candidate selection: candidate must have either start_payload, callback_data, or source_url.".to_string(),
        ))
    }

    /// Provides live search autocomplete suggestions.
    pub async fn get_suggestions(&self, query: &str, limit: usize) -> SearchSuggestionsResponse {
        let clean = query.trim().to_lowercase();
        if clean.is_empty() || clean.len() < 2 {
            return SearchSuggestionsResponse {
                query: query.to_string(),
                suggestions: Vec::new(),
            };
        }

        // Suggestions based on popular verified media catalog
        let catalog = [
            (1726, "Iron Man", "2008", "7.6", "After being held captive, Tony Stark creates a weaponized suit of armor."),
            (299536, "Avengers: Infinity War", "2018", "8.3", "The Avengers unite to battle the powerful Thanos."),
            (299534, "Avengers: Endgame", "2019", "8.3", "The remaining Avengers assemble once more to reverse Thanos' actions."),
            (27205, "Inception", "2010", "8.8", "A thief who steals corporate secrets through dream-sharing technology."),
            (157336, "Interstellar", "2014", "8.6", "A team of explorers travel through a wormhole in search of a new home."),
            (693134, "Dune: Part Two", "2024", "8.2", "Paul Atreides unites with Chani and the Fremen while seeking revenge."),
            (155, "The Dark Knight", "2008", "9.0", "Batman raises the stakes in his war on crime with the Joker."),
            (872585, "Oppenheimer", "2023", "8.1", "The story of American scientist J. Robert Oppenheimer and the Manhattan Project."),
            (438631, "Dune", "2021", "7.9", "Paul Atreides leads nomadic tribes in a battle for the desert planet Arrakis."),
            (19995, "Avatar", "2009", "7.9", "A paraplegic Marine dispatched to the moon Pandora on a unique mission."),
        ];

        let mut suggestions = Vec::new();
        for (id, title, year, rating, overview) in catalog {
            if title.to_lowercase().contains(&clean) {
                suggestions.push(SearchSuggestionItem {
                    id,
                    title: title.to_string(),
                    year: Some(year.to_string()),
                    rating: Some(rating.to_string()),
                    poster_url: None,
                    backdrop_url: None,
                    media_type: "movie".to_string(),
                    overview: overview.to_string(),
                });
                if suggestions.len() >= limit {
                    break;
                }
            }
        }

        SearchSuggestionsResponse {
            query: query.to_string(),
            suggestions,
        }
    }

    /// Simulated search execution for deterministic tests.
    async fn mock_search_movies(
        &self,
        _mock: &crate::services::telegram_auth::MockTelegramBackend,
        query: &str,
        page: i64,
        max_pages: i64,
    ) -> Result<SearchResponse, TelegramSearchError> {
        let lower = query.to_lowercase();

        // 1. Test simulated error conditions
        if lower.contains("test_timeout") {
            return Err(TelegramSearchError::Timeout(self.default_bot_username.clone(), 15));
        }
        if lower.contains("test_rate_limit") {
            return Err(TelegramSearchError::RateLimited(45));
        }
        if lower.contains("test_empty") {
            return Ok(SearchResponse {
                query: query.to_string(),
                candidates: Vec::new(),
                title_groups: HashMap::new(),
                pagination: Some(SearchPaginationInfo {
                    current_page: 1,
                    total_pages: 1,
                    total_results: 0,
                    has_next: false,
                    has_prev: false,
                    next_callback_data: None,
                    prev_callback_data: None,
                    source_message_id: Some(100),
                }),
                channel_requirement: None,
                metadata_enrichment: HashMap::new(),
                is_cached: false,
                error: None,
            });
        }
        if lower.contains("test_fsub") {
            let req = ChannelRequirement {
                required: true,
                channel_title: Some("Cineforge Updates".to_string()),
                channel_username: Some("cineforge_updates".to_string()),
                invite_url: Some("https://t.me/+join_cineforge_channel".to_string()),
                message: "You must join our Telegram channel @cineforge_updates to search and stream media.".to_string(),
            };
            return Ok(SearchResponse {
                query: query.to_string(),
                candidates: Vec::new(),
                title_groups: HashMap::new(),
                pagination: None,
                channel_requirement: Some(req),
                metadata_enrichment: HashMap::new(),
                is_cached: false,
                error: None,
            });
        }

        // 2. Generate simulated multi-quality search results for standard queries
        let display_title = if lower.contains("inception") {
            "Inception (2010)"
        } else if lower.contains("interstellar") {
            "Interstellar (2014)"
        } else if lower.contains("dune") {
            "Dune: Part Two (2024)"
        } else {
            query
        };

        let raw_buttons = vec![
            RawInlineButton {
                text: format!("🎬 {} [2160p 4K UHD HDR Atmos] (8.4 GB) mkv", display_title),
                callback_data: Some(format!("cand_{}_4k", page)),
                url: None,
            },
            RawInlineButton {
                text: format!("🎬 {} [1080p Web-DL Multi-Audio] (2.8 GB) mp4", display_title),
                callback_data: Some(format!("cand_{}_1080p", page)),
                url: None,
            },
            RawInlineButton {
                text: format!("🎬 {} [720p Mobile Fast Stream] (980 MB) mp4", display_title),
                callback_data: Some(format!("cand_{}_720p", page)),
                url: None,
            },
            RawInlineButton {
                text: format!("{}/3", page),
                callback_data: None,
                url: None,
            },
            RawInlineButton {
                text: "Next >>".to_string(),
                callback_data: if page < 3 { Some(format!("page_{}", page + 1)) } else { None },
                url: None,
            },
        ];

        let msg = RawBotMessage {
            message_id: 1000 + page,
            text: format!("Results for '{}'\nTotal Results: 15\nPage: {}/3", query, page),
            buttons: raw_buttons,
        };

        let (mut candidates, mut title_groups, mut pagination, channel_req) =
            parse_bot_response(&msg, &self.default_bot_username, page);

        // Progressive page aggregation simulation
        if max_pages > 1 && page == 1 && pagination.has_next {
            let page2_buttons = vec![
                RawInlineButton {
                    text: format!("🎬 {} [1080p HEVC BluRay x265] (1.6 GB) mkv", display_title),
                    callback_data: Some("cand_2_1080p_hevc".to_string()),
                    url: None,
                },
                RawInlineButton {
                    text: format!("🎬 {} [480p SD Mobile Stream] (450 MB) mp4", display_title),
                    callback_data: Some("cand_2_480p".to_string()),
                    url: None,
                },
            ];

            let msg_page2 = RawBotMessage {
                message_id: 1002,
                text: format!("Results for '{}'\nTotal Results: 15\nPage: 2/3", query),
                buttons: page2_buttons,
            };

            let (p2_candidates, _, _, _) =
                parse_bot_response(&msg_page2, &self.default_bot_username, 2);

            for cand in p2_candidates {
                title_groups
                    .entry(cand.title.clone())
                    .or_default()
                    .push(cand.clone());
                candidates.push(cand);
            }
            pagination.current_page = 2;
        }

        Ok(SearchResponse {
            query: query.to_string(),
            candidates,
            title_groups,
            pagination: Some(pagination),
            channel_requirement: channel_req,
            metadata_enrichment: HashMap::new(),
            is_cached: false,
            error: None,
        })
    }

    /// Real MTProto bot interaction using authenticated Telegram client.
    async fn mtproto_search_movies(
        &self,
        mtproto: &crate::services::telegram_auth::MtprotoTelegramBackend,
        query: &str,
        page: i64,
        _max_pages: i64,
    ) -> Result<SearchResponse, TelegramSearchError> {
        let client = mtproto.get_client().await.map_err(TelegramSearchError::General)?;
        let is_authed = client.is_authorized().await.map_err(|e| TelegramSearchError::General(e.to_string()))?;
        if !is_authed {
            return Err(TelegramSearchError::NotConnected);
        }

        let bot_username = self.default_bot_username.clone();
        log::info!("Initiating Telegram search for query '{}' via bot @{}", query, bot_username);

        // 1. Resolve bot peer
        let resolved = client
            .invoke(&grammers_tl_types::functions::contacts::ResolveUsername {
                username: bot_username.clone(),
                referer: None,
            })
            .await
            .map_err(|e| {
                TelegramSearchError::General(format!("Failed to resolve bot @{bot_username}: {e}"))
            })?;

        let bot_peer = match resolved {
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
                _ => return Err(TelegramSearchError::General("Resolved peer is not a user or bot".to_string())),
            },
        };

        // 2. Send search query message to bot in private chat
        let random_id = {
            use std::time::SystemTime;
            let nanos = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos();
            nanos as i64
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
            message: query.to_string(),
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
            TelegramSearchError::General(format!("Failed to send search query to bot: {e}"))
        })?;

        // 3. Poll for the bot's response message with timeout
        let poll_start = std::time::Instant::now();
        let timeout_limit = Duration::from_secs(12);

        let mut bot_response_msg: Option<RawBotMessage> = None;

        while poll_start.elapsed() < timeout_limit {
            tokio::time::sleep(Duration::from_millis(800)).await;

            let history_req = grammers_tl_types::functions::messages::GetHistory {
                peer: bot_peer.clone(),
                offset_id: 0,
                offset_date: 0,
                add_offset: 0,
                limit: 5,
                max_id: 0,
                min_id: 0,
                hash: 0,
            };

            if let Ok(hist) = client.invoke(&history_req).await {
                let msgs = match hist {
                    grammers_tl_types::enums::messages::Messages::Messages(m) => m.messages,
                    grammers_tl_types::enums::messages::Messages::Slice(s) => s.messages,
                    grammers_tl_types::enums::messages::Messages::ChannelMessages(c) => c.messages,
                    grammers_tl_types::enums::messages::Messages::NotModified(_) => vec![],
                };

                for m in msgs {
                    if let grammers_tl_types::enums::Message::Message(msg) = m {
                        // Incoming message from the bot (not sent by us)
                        if !msg.out {
                            let text = msg.message;
                            let mut raw_buttons = Vec::new();

                            if let Some(markup) = msg.reply_markup {
                                if let grammers_tl_types::enums::ReplyMarkup::ReplyInlineMarkup(inline) = markup {
                                    for row in inline.rows {
                                        let grammers_tl_types::enums::KeyboardInlineButtonRow::Row(r) = row;
                                        for btn in r.buttons {
                                            let grammers_tl_types::enums::KeyboardInlineButton::Button(b) = btn;
                                            match b.r#type {
                                                grammers_tl_types::enums::InlineButtonType::Callback(cb) => {
                                                    let cb_str = String::from_utf8_lossy(&cb.data).to_string();
                                                    raw_buttons.push(RawInlineButton {
                                                        text: b.text,
                                                        callback_data: Some(cb_str),
                                                        url: None,
                                                    });
                                                }
                                                grammers_tl_types::enums::InlineButtonType::Url(u) => {
                                                    raw_buttons.push(RawInlineButton {
                                                        text: b.text,
                                                        callback_data: None,
                                                        url: Some(u.url),
                                                    });
                                                }
                                                _ => {}
                                            }
                                        }
                                    }
                                }
                            }

                            bot_response_msg = Some(RawBotMessage {
                                message_id: msg.id as i64,
                                text,
                                buttons: raw_buttons,
                            });
                            break;
                        }
                    }
                }

                if bot_response_msg.is_some() {
                    break;
                }
            }
        }

        let resp_msg = match bot_response_msg {
            Some(m) => m,
            None => {
                return Err(TelegramSearchError::Timeout(bot_username, 12));
            }
        };

        let (candidates, title_groups, pagination, channel_req) =
            parse_bot_response(&resp_msg, &bot_username, page);

        Ok(SearchResponse {
            query: query.to_string(),
            candidates,
            title_groups,
            pagination: Some(pagination),
            channel_requirement: channel_req,
            metadata_enrichment: HashMap::new(),
            is_cached: false,
            error: None,
        })
    }
}
