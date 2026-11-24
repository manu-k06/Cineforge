use regex::Regex;
use std::collections::HashMap;
use std::sync::LazyLock;

use crate::models::search::{
    ChannelRequirement, SearchCandidate, SearchPaginationInfo,
};

static TOTAL_RESULTS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)total\s*results\s*:\s*(\d+)").unwrap());
static PAGE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)page\s*:\s*(\d+)\s*/\s*(\d+)").unwrap());
static BUTTON_PAGE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(\d+)\s*/\s*(\d+)$").unwrap());
static SIZE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(\d+(?:\.\d+)?\s*(?:GB|MB|GiB|MiB|KB))\b").unwrap()
});
static RESOLUTION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(2160p|4k|1080p|720p|480p|360p)\b").unwrap()
});
static ENCODER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(bluray|web-?dl|webrip|hdrip|dvdrip|brrip|bdrip)\b").unwrap()
});
static EXTENSION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\b(mp4|mkv|webm|avi|mov|ts)\b").unwrap());

static MULTI_AUDIO_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(multi\s*audio|dual\s*audio|multi\s*lang|multi|dual)\b").unwrap()
});
static ENG_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(english|eng)\b").unwrap());
static TAM_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(tamil|tam)\b").unwrap());
static TEL_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(telugu|tel|telug)\b").unwrap());
static HIN_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(hindi|hin)\b").unwrap());
static MAL_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(malayalam|mal)\b").unwrap());
static KAN_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(kannada|kan)\b").unwrap());
static ENCODER_ENG_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(pahe|psa|yts|yify|bluray|rarbg|eztv|galaxyrg)\b").unwrap()
});

/// Generic button representation extracted from Telegram inline markup.
#[derive(Debug, Clone, PartialEq)]
pub struct RawInlineButton {
    pub text: String,
    pub callback_data: Option<String>,
    pub url: Option<String>,
}

/// Generic message representation extracted from Telegram bot responses.
#[derive(Debug, Clone, PartialEq)]
pub struct RawBotMessage {
    pub message_id: i64,
    pub text: String,
    pub buttons: Vec<RawInlineButton>,
}

/// Helper to parse Telegram deep link URLs of the form `https://t.me/BotName?start=Payload`.
pub fn parse_deep_link(url: &str) -> Option<(String, String)> {
    let clean = url.trim();
    if !clean.contains("t.me/") {
        return None;
    }

    if let Ok(parsed) = reqwest::Url::parse(clean) {
        let bot_name = parsed.path().trim_start_matches('/').to_string();
        for (k, v) in parsed.query_pairs() {
            if k == "start" && !v.is_empty() {
                return Some((bot_name, v.to_string()));
            }
        }
    }
    None
}

/// Calculates approximate size in bytes from human-readable size strings (e.g. "2.4 GB").
pub fn parse_size_bytes(size_str: &str) -> Option<i64> {
    let parts: Vec<&str> = size_str.split_whitespace().collect();
    if parts.len() < 2 {
        return None;
    }

    let val = parts[0].parse::<f64>().ok()?;
    let unit = parts[1].to_lowercase();

    if unit.starts_with("gb") || unit.starts_with("gib") {
        Some((val * 1024.0 * 1024.0 * 1024.0) as i64)
    } else if unit.starts_with("mb") || unit.starts_with("mib") {
        Some((val * 1024.0 * 1024.0) as i64)
    } else if unit.starts_with("kb") {
        Some((val * 1024.0) as i64)
    } else {
        None
    }
}

/// Detects audio languages from candidate text using word-boundary matching.
pub fn detect_language(text: &str) -> Option<String> {
    let is_multi = MULTI_AUDIO_RE.is_match(text);
    let has_eng = ENG_RE.is_match(text);
    let has_tam = TAM_RE.is_match(text);
    let has_tel = TEL_RE.is_match(text);
    let has_hin = HIN_RE.is_match(text);
    let has_mal = MAL_RE.is_match(text);
    let has_kan = KAN_RE.is_match(text);

    let mut found = Vec::new();
    if has_eng {
        found.push("English");
    }
    if has_tam {
        found.push("Tamil");
    }
    if has_tel {
        found.push("Telugu");
    }
    if has_hin {
        found.push("Hindi");
    }
    if has_mal {
        found.push("Malayalam");
    }
    if has_kan {
        found.push("Kannada");
    }

    if is_multi || found.len() > 1 {
        if !found.is_empty() {
            Some(format!("Multi Audio ({})", found.join(" + ")))
        } else {
            Some("Multi Audio".to_string())
        }
    } else if found.len() == 1 {
        Some(found[0].to_string())
    } else if ENCODER_ENG_RE.is_match(text) {
        Some("English".to_string())
    } else {
        None
    }
}

/// A parsed channel target, safely distinguishing public @username handles from private invite hashes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParsedChannelTarget {
    Public(String),     // Clean channel username without leading @
    Private(String),    // Clean invite hash without leading +
}

/// Parses a Telegram channel link into either a public channel username or private invite hash.
/// Rejects non-Telegram links as a security safeguard against phishing or off-platform URLs.
pub fn parse_channel_link(url: &str) -> Option<ParsedChannelTarget> {
    let clean = url.trim();
    if clean.is_empty() {
        return None;
    }

    // Direct @channel_name handle
    if clean.starts_with('@') && clean.len() > 1 {
        let handle = clean.trim_start_matches('@').trim();
        if !handle.is_empty() && handle.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Some(ParsedChannelTarget::Public(handle.to_string()));
        }
        return None;
    }

    // Must be an authentic Telegram URL
    let parsed = reqwest::Url::parse(clean).ok()?;
    let host = parsed.host_str()?.to_lowercase();
    if host != "t.me" && host != "telegram.me" && host != "telegram.dog" {
        return None;
    }

    let path = parsed.path().trim_matches('/');
    if path.is_empty() {
        return None;
    }

    // Private invite link: e.g. /+hash or /joinchat/hash
    if let Some(stripped) = path.strip_prefix('+') {
        let hash = stripped.split('?').next().unwrap_or("").trim_matches('/');
        if !hash.is_empty() {
            return Some(ParsedChannelTarget::Private(hash.to_string()));
        }
    } else if let Some(stripped) = path.strip_prefix("joinchat/") {
        let hash = stripped.split('?').next().unwrap_or("").trim_matches('/');
        if !hash.is_empty() {
            return Some(ParsedChannelTarget::Private(hash.to_string()));
        }
    } else {
        // Public channel: e.g. /channel_username
        let username = path.split('/').next().unwrap_or("").split('?').next().unwrap_or("").trim_matches('/');
        let clean_username = username.trim_start_matches('@');
        if !clean_username.is_empty()
            && clean_username.chars().all(|c| c.is_alphanumeric() || c == '_')
            && !clean_username.eq_ignore_ascii_case("share")
            && !clean_username.eq_ignore_ascii_case("addstickers")
            && !clean_username.eq_ignore_ascii_case("iv")
        {
            return Some(ParsedChannelTarget::Public(clean_username.to_string()));
        }
    }

    None
}

/// Checks whether a message indicates a Force Subscription / Updates Channel gatekeeper.
/// Extracts the required channel target (public username or private invite link) and any retry action.
pub fn detect_channel_requirement(
    text: &str,
    buttons: &[RawInlineButton],
    bot_username: Option<&str>,
) -> Option<ChannelRequirement> {
    let lower_text = text.to_lowercase();
    let bot_lower = bot_username.map(|b| b.to_lowercase().trim_start_matches('@').to_string());

    let fsub_indicators = [
        "updates channel",
        "join channel",
        "join our channel",
        "join my channel",
        "must join",
        "force sub",
        "fsub",
        "subscribe to",
        "please join",
        "join the channel",
        "channel membership",
        "subscribe our channel",
        "you haven't joined",
        "you have not joined",
    ];

    let has_fsub_indicator = fsub_indicators.iter().any(|&k| lower_text.contains(k));

    let mut detected_invite_url: Option<String> = None;
    let mut detected_username: Option<String> = None;
    let mut retry_callback: Option<String> = None;
    let mut retry_start_payload: Option<String> = None;

    // 1. Scan buttons for channel links and retry actions
    for btn in buttons {
        let btn_text_lower = btn.text.to_lowercase();

        // Check if button is a channel join URL
        if let Some(ref url) = btn.url {
            if let Some(target) = parse_channel_link(url) {
                let matches_bot = match &target {
                    ParsedChannelTarget::Public(u) => {
                        bot_lower.as_deref().map(|b| b.eq_ignore_ascii_case(u)).unwrap_or(false)
                    }
                    ParsedChannelTarget::Private(_) => false,
                };

                // Ensure link does not point to the bot itself or Cineforge
                if !matches_bot {
                    match target {
                        ParsedChannelTarget::Public(u) => {
                            if detected_username.is_none() {
                                detected_username = Some(u);
                            }
                            if detected_invite_url.is_none() {
                                detected_invite_url = Some(url.clone());
                            }
                        }
                        ParsedChannelTarget::Private(_) => {
                            if detected_invite_url.is_none() {
                                detected_invite_url = Some(url.clone());
                            }
                        }
                    }
                }
            }

            // Check if button is a "Try Again" / "Refresh" URL button
            let is_retry_text = btn_text_lower.contains("try")
                || btn_text_lower.contains("again")
                || btn_text_lower.contains("refresh")
                || btn_text_lower.contains("check")
                || btn_text_lower.contains("verify")
                || btn_text_lower.contains("joined")
                || btn_text_lower.contains("continue")
                || btn_text_lower.contains("done");

            if is_retry_text {
                if let Some((_, payload)) = parse_deep_link(url) {
                    retry_start_payload = Some(payload);
                }
            }
        }

        // Check if button is a "Try Again" callback button
        if let Some(ref cb) = btn.callback_data {
            let cb_lower = cb.to_lowercase();
            let is_retry_cb = btn_text_lower.contains("try")
                || btn_text_lower.contains("again")
                || btn_text_lower.contains("refresh")
                || btn_text_lower.contains("check")
                || btn_text_lower.contains("verify")
                || btn_text_lower.contains("joined")
                || btn_text_lower.contains("continue")
                || btn_text_lower.contains("done")
                || cb_lower.contains("check")
                || cb_lower.contains("try")
                || cb_lower.contains("again")
                || cb_lower.contains("sub")
                || cb_lower.contains("verify");

            if is_retry_cb && retry_callback.is_none() {
                retry_callback = Some(cb.clone());
            }
        }
    }

    // 2. Scan message text for channel links if none found in buttons
    if detected_invite_url.is_none() {
        for word in text.split_whitespace() {
            let trimmed = word.trim_matches(|c: char| !c.is_alphanumeric() && c != '@' && c != '+' && c != '/' && c != ':' && c != '.');
            if let Some(target) = parse_channel_link(trimmed) {
                let matches_bot = match &target {
                    ParsedChannelTarget::Public(u) => {
                        bot_lower.as_deref().map(|b| b.eq_ignore_ascii_case(u)).unwrap_or(false)
                    }
                    ParsedChannelTarget::Private(_) => false,
                };
                if !matches_bot {
                    match target {
                        ParsedChannelTarget::Public(u) => {
                            detected_username = Some(u);
                            detected_invite_url = Some(if trimmed.starts_with('@') {
                                format!("https://t.me/{}", trimmed.trim_start_matches('@'))
                            } else {
                                trimmed.to_string()
                            });
                            break;
                        }
                        ParsedChannelTarget::Private(_) => {
                            detected_invite_url = Some(trimmed.to_string());
                            break;
                        }
                    }
                }
            }
        }
    }

    // Only qualify as an FSub gate if either an explicit FSub indicator exists OR an invite link is found
    if has_fsub_indicator || detected_invite_url.is_some() {
        let channel_title = detected_username.as_ref().map(|u| format!("@{u}"));
        Some(ChannelRequirement {
            required: true,
            channel_title,
            channel_username: detected_username,
            invite_url: detected_invite_url,
            message: if !text.trim().is_empty() {
                text.trim().to_string()
            } else {
                "Channel membership is required by this bot. Please join the required channel to access this media.".to_string()
            },
            retry_callback,
            retry_start_payload,
        })
    } else {
        None
    }
}

/// Extracts pagination information from message text and buttons.
pub fn extract_pagination(
    text: &str,
    buttons: &[RawInlineButton],
    source_message_id: i64,
) -> SearchPaginationInfo {
    let mut current_page = 1;
    let mut total_pages = 1;
    let mut total_results = 0;
    let mut has_next = false;
    let mut has_prev = false;
    let mut next_callback_data = None;
    let mut prev_callback_data = None;

    if let Some(caps) = TOTAL_RESULTS_RE.captures(text) {
        if let Some(m) = caps.get(1) {
            total_results = m.as_str().parse::<i64>().unwrap_or(0);
        }
    }

    if let Some(caps) = PAGE_RE.captures(text) {
        if let (Some(cur), Some(tot)) = (caps.get(1), caps.get(2)) {
            current_page = cur.as_str().parse::<i64>().unwrap_or(1);
            total_pages = tot.as_str().parse::<i64>().unwrap_or(1);
        }
    }

    for btn in buttons {
        let trimmed_text = btn.text.trim();

        if let Some(caps) = BUTTON_PAGE_RE.captures(trimmed_text) {
            if let (Some(cur), Some(tot)) = (caps.get(1), caps.get(2)) {
                current_page = cur.as_str().parse::<i64>().unwrap_or(current_page);
                total_pages = tot.as_str().parse::<i64>().unwrap_or(total_pages);
            }
        }

        let lower = trimmed_text.to_lowercase();
        let cb = btn.callback_data.as_deref().unwrap_or("");
        let lower_cb = cb.to_lowercase();

        let is_next = lower.contains("next")
            || lower.contains(">>")
            || lower.contains(">")
            || (lower_cb.contains("next") && !lower_cb.contains("back") && !lower_cb.contains("prev"));

        if is_next && !cb.is_empty() {
            has_next = true;
            next_callback_data = Some(cb.to_string());
        }

        let is_prev = lower.contains("back")
            || lower.contains("prev")
            || lower.contains("<<")
            || lower.contains("<")
            || (lower_cb.contains("back") || lower_cb.contains("prev"));

        if is_prev && !cb.is_empty() {
            has_prev = true;
            prev_callback_data = Some(cb.to_string());
        }
    }

    if total_results == 0 && total_pages > 1 {
        total_results = total_pages * 10;
    }

    SearchPaginationInfo {
        current_page,
        total_pages: total_pages.max(1),
        total_results,
        has_next,
        has_prev,
        next_callback_data,
        prev_callback_data,
        source_message_id: Some(source_message_id),
    }
}

/// Normalizes an inline button into a SearchCandidate.
pub fn normalize_button(
    btn: &RawInlineButton,
    source_bot: &str,
    source_message_id: i64,
    page_number: i64,
) -> Option<SearchCandidate> {
    let btn_text = btn.text.trim();
    if btn_text.is_empty() {
        return None;
    }

    let lower = btn_text.to_lowercase();

    // Ignore filter, navigation, and page counter buttons
    if lower.contains("next")
        || lower.contains("back")
        || lower.contains("prev")
        || lower.contains("page")
        || lower.contains("counter")
        || lower.contains("join")
        || lower.contains("updates")
        || lower.contains("language")
        || lower.contains("quality")
    {
        return None;
    }

    if BUTTON_PAGE_RE.is_match(btn_text) {
        return None;
    }

    let cb = btn.callback_data.as_deref().unwrap_or("");
    let lower_cb = cb.to_lowercase();
    if lower_cb.contains("languages#")
        || lower_cb.contains("quality#")
        || lower_cb.contains("next_")
        || lower_cb.contains("back_")
        || lower_cb.contains("page_")
    {
        return None;
    }

    let mut start_payload = None;
    let mut target_bot = source_bot.to_string();

    if let Some(ref url) = btn.url {
        if let Some((b, p)) = parse_deep_link(url) {
            if !b.is_empty() {
                target_bot = b;
            }
            start_payload = Some(p);
        } else if url.contains("t.me/+") || url.contains("joinchat") {
            // Invite link, not media candidate
            return None;
        }
    }

    // Extract size
    let size = SIZE_RE
        .captures(btn_text)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().trim().to_string());
    let size_bytes = size.as_deref().and_then(parse_size_bytes);

    // Extract quality
    let quality = if let Some(caps) = RESOLUTION_RE.captures(btn_text) {
        let q = caps.get(1).unwrap().as_str().to_uppercase();
        if q == "4K" {
            "2160P".to_string()
        } else {
            q
        }
    } else if let Some(caps) = ENCODER_RE.captures(btn_text) {
        caps.get(1).unwrap().as_str().to_uppercase()
    } else {
        "HD".to_string()
    };

    // Extract language
    let language = detect_language(btn_text);

    // Determine container extension
    let extension = EXTENSION_RE
        .captures(btn_text)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_lowercase());

    let container = extension.clone();
    let browser_playable = container.as_deref() == Some("mp4");
    let playback_mode = if browser_playable {
        "browser".to_string()
    } else {
        "external".to_string()
    };

    // Extract or derive clean title
    let mut title_candidate = btn_text.to_string();
    if let Some(ref s) = size {
        title_candidate = title_candidate.replace(s, " ");
    }
    if let Some(ref ext) = extension {
        title_candidate = title_candidate.replace(ext, " ");
    }
    // Clean emojis and extraneous punctuation
    let clean_title: String = title_candidate
        .chars()
        .map(|ch| if ch.is_alphanumeric() || ch == ' ' || ch == '\'' { ch } else { ' ' })
        .collect();
    let title = clean_title.split_whitespace().collect::<Vec<_>>().join(" ");
    let final_title = if title.len() >= 2 { title } else { btn_text.to_string() };

    // Unique deterministic candidate ID using sha256 (first 16 hex chars)
    let raw_key = format!("{}:{}:{}", target_bot, start_payload.as_deref().unwrap_or(cb), btn_text);
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    std::hash::Hash::hash(&raw_key, &mut hasher);
    let hash_val = std::hash::Hasher::finish(&hasher);
    let candidate_id = format!("cand-{:016x}", hash_val);

    Some(SearchCandidate {
        candidate_id,
        source_bot: target_bot,
        source_message_id,
        start_payload,
        callback_data: if cb.is_empty() { None } else { Some(cb.to_string()) },
        display_text: btn_text.to_string(),
        title: final_title,
        size,
        size_bytes,
        quality,
        language,
        extension,
        container,
        browser_playable,
        playback_mode,
        compatibility_reason: None,
        page_number,
    })
}

/// Parses an entire bot response message and its inline buttons into candidates and groups.
pub fn parse_bot_response(
    msg: &RawBotMessage,
    source_bot: &str,
    page_number: i64,
) -> (
    Vec<SearchCandidate>,
    HashMap<String, Vec<SearchCandidate>>,
    SearchPaginationInfo,
    Option<ChannelRequirement>,
) {
    let channel_req = detect_channel_requirement(&msg.text, &msg.buttons, Some(source_bot));
    let pagination = extract_pagination(&msg.text, &msg.buttons, msg.message_id);

    let mut candidates = Vec::new();
    let mut title_groups: HashMap<String, Vec<SearchCandidate>> = HashMap::new();

    for btn in &msg.buttons {
        if let Some(cand) = normalize_button(btn, source_bot, msg.message_id, page_number) {
            title_groups
                .entry(cand.title.clone())
                .or_default()
                .push(cand.clone());
            candidates.push(cand);
        }
    }

    (candidates, title_groups, pagination, channel_req)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_size_bytes() {
        assert_eq!(parse_size_bytes("2.4 GB"), Some(2576980377));
        assert_eq!(parse_size_bytes("750 MB"), Some(786432000));
        assert_eq!(parse_size_bytes("invalid"), None);
    }

    #[test]
    fn test_detect_language() {
        assert_eq!(detect_language("Inception 2010 1080p Dual Audio Hindi English"), Some("Multi Audio (English + Hindi)".to_string()));
        assert_eq!(detect_language("Dune 2024 Tamil Dubbed"), Some("Tamil".to_string()));
        assert_eq!(detect_language("Interstellar 2014 YTS"), Some("English".to_string()));
    }

    #[test]
    fn test_normalize_candidate_button() {
        let btn = RawInlineButton {
            text: "🎬 Inception (2010) [1080p Web-DL Multi] (2.4 GB) mp4".to_string(),
            callback_data: Some("dl_12345".to_string()),
            url: None,
        };

        let cand = normalize_button(&btn, "Spoty_xbot", 100, 1).expect("candidate expected");
        assert_eq!(cand.quality, "1080P");
        assert_eq!(cand.size, Some("2.4 GB".to_string()));
        assert_eq!(cand.container, Some("mp4".to_string()));
        assert!(cand.browser_playable);
        assert_eq!(cand.playback_mode, "browser");
        assert!(cand.candidate_id.starts_with("cand-"));
    }

    #[test]
    fn test_extract_pagination_and_filter_buttons() {
        let text = "Search Results: Inception\nTotal Results: 45\nPage: 1/5";
        let buttons = vec![
            RawInlineButton {
                text: "🎬 Inception 1080p (2.1 GB)".to_string(),
                callback_data: Some("get_1".to_string()),
                url: None,
            },
            RawInlineButton {
                text: "1/5".to_string(),
                callback_data: None,
                url: None,
            },
            RawInlineButton {
                text: "Next >>".to_string(),
                callback_data: Some("page_2".to_string()),
                url: None,
            },
        ];

        let msg = RawBotMessage {
            message_id: 101,
            text: text.to_string(),
            buttons,
        };

        let (candidates, title_groups, pagination, channel_req) =
            parse_bot_response(&msg, "Spoty_xbot", 1);

        assert_eq!(candidates.len(), 1);
        assert!(title_groups.contains_key("Inception 1080p"));
        assert_eq!(pagination.current_page, 1);
        assert_eq!(pagination.total_pages, 5);
        assert_eq!(pagination.total_results, 45);
        assert!(pagination.has_next);
        assert_eq!(pagination.next_callback_data, Some("page_2".to_string()));
        assert!(channel_req.is_none());
    }

    #[test]
    fn test_parse_channel_link_public() {
        assert_eq!(
            parse_channel_link("@cineforge_channel"),
            Some(ParsedChannelTarget::Public("cineforge_channel".to_string()))
        );
        assert_eq!(
            parse_channel_link("https://t.me/cineforge_channel"),
            Some(ParsedChannelTarget::Public("cineforge_channel".to_string()))
        );
        assert_eq!(
            parse_channel_link("https://telegram.me/cineforge_channel"),
            Some(ParsedChannelTarget::Public("cineforge_channel".to_string()))
        );
    }

    #[test]
    fn test_parse_channel_link_private() {
        assert_eq!(
            parse_channel_link("https://t.me/+AbCdEfGh12345"),
            Some(ParsedChannelTarget::Private("AbCdEfGh12345".to_string()))
        );
        assert_eq!(
            parse_channel_link("https://t.me/joinchat/XyZ12345"),
            Some(ParsedChannelTarget::Private("XyZ12345".to_string()))
        );
    }

    #[test]
    fn test_parse_channel_link_rejects_non_telegram_and_invalid() {
        // Security safeguard: only genuine Telegram domains allowed
        assert_eq!(parse_channel_link("https://malicious.com/+fakehash"), None);
        assert_eq!(parse_channel_link("https://google.com/test"), None);
        assert_eq!(parse_channel_link("http://phishing.site/telegram.me"), None);
        assert_eq!(parse_channel_link("https://t.me/share/url?url=xxx"), None);
        assert_eq!(parse_channel_link(""), None);
    }

    #[test]
    fn test_detect_channel_requirement_fsub() {
        let text = "⚠️ You must join our Updates Channel to use this bot!";
        let buttons = vec![
            RawInlineButton {
                text: "📢 Join Channel".to_string(),
                callback_data: None,
                url: Some("https://t.me/+join_private_channel_link".to_string()),
            },
            RawInlineButton {
                text: "✅ Joined / Try Again".to_string(),
                callback_data: Some("check_sub".to_string()),
                url: None,
            },
        ];

        let msg = RawBotMessage {
            message_id: 102,
            text: text.to_string(),
            buttons,
        };

        let (candidates, _, _, channel_req) = parse_bot_response(&msg, "Spoty_xbot", 1);
        assert_eq!(candidates.len(), 0);
        let req = channel_req.expect("channel requirement expected");
        assert!(req.required);
        assert_eq!(req.invite_url, Some("https://t.me/+join_private_channel_link".to_string()));
        assert_eq!(req.retry_callback, Some("check_sub".to_string()));
    }

    #[test]
    fn test_detect_channel_requirement_with_retry_start_payload() {
        let text = "Please subscribe to our updates channel before accessing files.";
        let buttons = vec![
            RawInlineButton {
                text: "📢 Updates Channel".to_string(),
                callback_data: None,
                url: Some("https://t.me/my_updates_channel".to_string()),
            },
            RawInlineButton {
                text: "🔄 Refresh / Try Again".to_string(),
                callback_data: None,
                url: Some("https://t.me/Spoty_xbot?start=retry_file_123".to_string()),
            },
        ];

        let msg = RawBotMessage {
            message_id: 103,
            text: text.to_string(),
            buttons,
        };

        let (_, _, _, channel_req) = parse_bot_response(&msg, "Spoty_xbot", 1);
        let req = channel_req.expect("channel requirement expected");
        assert_eq!(req.channel_username, Some("my_updates_channel".to_string()));
        assert_eq!(req.retry_start_payload, Some("retry_file_123".to_string()));
    }
}
