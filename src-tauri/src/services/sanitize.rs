use regex::Regex;
use std::sync::LazyLock;
use std::time::{SystemTime, UNIX_EPOCH};

static BRACKET_SIZE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\[\s*[\d\.]+\s*(?:MB|GB|GiB|MiB)\s*\]").unwrap()
});

static EXT_END_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\.(?:mkv|mp4|avi|webm|mov)$").unwrap()
});

static EXT_WORD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:mkv|mp4|avi|webm|mov)\b").unwrap()
});

static YEAR_RES_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(19\d\d|20[0-2]\d)((?:2160|1080|720|480|360)\s*p)").unwrap()
});

static YEAR_WORD_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(19\d\d|20[0-2]\d)([a-zA-Z]+)").unwrap()
});

static WORD_YEAR_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"([a-zA-Z]+)(19\d\d|20[0-2]\d)").unwrap()
});

static AMPERSAND_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\s*&\s*").unwrap()
});

static TELEGRAM_HANDLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"@[\w\d_]+").unwrap()
});

static WATERMARK_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:\d*|www\.)?(?:tamilmv|tamilblasters|cinemavilla|moviesda|filmywap|cineforge|spoty_xbot)[\w\.-]*").unwrap()
});

static BRACKETS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"[\[\]\(\)]").unwrap()
});

static SEPARATORS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"[._\-–—]").unwrap()
});

static TV_SEASON_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:s\d{1,2}\s*[eex]\d{1,3}|season\s*\d+|s\d{1,2}|ep(?:isode)?\s*\d+)\b.*").unwrap()
});

static YEAR_MATCH_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b(19\d\d|20[0-2]\d)\b").unwrap()
});

static JUNK_PATTERN_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r"(?i)\b(1080\s*p|720\s*p|480\s*p|2160\s*p|4k|uhd|bluray|bdrip|brrip|dvdrip|web-?dl|webrip|hdrip|x264|x265|",
        r"hevc|aac|dts|remux|dual\s*audio|multi\s*audio|multi\s*sub|msubs?|esubs?|",
        r"proper|repack|org\s*audio|tamildubbed|tamil|telugu|hindi|malayalam|kannada|english|",
        r"engbray\w*|bray\w*|bluray\w*|bdrip\w*|brrip\w*)\b.*"
    )).unwrap()
});

static WHITESPACE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\s+").unwrap()
});

fn get_current_year() -> i32 {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Howard Hinnant's civil date algorithm from UNIX days
    let days = (secs / 86400) as i64;
    let z = days + 719468;
    let era = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1024 + doe / 1461 - doe / 14245) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }) as i32
}

/// Extract a clean movie title and optional release year from messy release strings.
/// Parallels the Python backend's `sanitize_movie_query`.
/// Example: '@KCFilmss - The Greatest of All Time 2024 Dual Audio 1080p.mkv' -> ('The Greatest of All Time', Some(2024))
pub fn sanitize_movie_query(raw_title: &str) -> (String, Option<i32>) {
    if raw_title.trim().is_empty() {
        return (String::new(), None);
    }

    // Strip bracket size tags
    let mut text = BRACKET_SIZE_RE.replace_all(raw_title, "").to_string();
    // Strip file extensions
    text = EXT_END_RE.replace_all(&text, "").to_string();
    text = EXT_WORD_RE.replace_all(&text, "").to_string();
    // Split year and resolution
    text = YEAR_RES_RE.replace_all(&text, "$1 $2").to_string();
    // Split year and format words
    text = YEAR_WORD_RE.replace_all(&text, "$1 $2").to_string();
    text = WORD_YEAR_RE.replace_all(&text, "$1 $2").to_string();
    // Normalize ampersands
    text = AMPERSAND_RE.replace_all(&text, " and ").to_string();
    // Strip Telegram handles
    text = TELEGRAM_HANDLE_RE.replace_all(&text, "").to_string();
    // Strip pirate site watermarks
    text = WATERMARK_RE.replace_all(&text, "").to_string();
    // Replace brackets and separators with spaces
    text = BRACKETS_RE.replace_all(&text, " ").to_string();
    text = SEPARATORS_RE.replace_all(&text, " ").to_string();
    // Strip TV season/episode tags
    text = TV_SEASON_RE.replace_all(&text, "").to_string();

    let current_year = get_current_year();
    let max_valid_year = current_year + 2;
    let mut year: Option<i32> = None;

    let year_matches: Vec<_> = YEAR_MATCH_RE.find_iter(&text).collect();
    if !year_matches.is_empty() {
        let first_match = &year_matches[0];
        let word_count = text.split_whitespace().count();

        // If the only match is at the start (index 0) with multiple words, keep (e.g. '1917', '2001 A Space Odyssey')
        if year_matches.len() == 1 && first_match.start() == 0 && word_count > 1 {
            // Keep in title
        } else {
            let last_m = year_matches.last().unwrap();
            if let Ok(cand_y) = last_m.as_str().parse::<i32>() {
                if (1900..=max_valid_year).contains(&cand_y) {
                    year = Some(cand_y);
                    text = text[..last_m.start()].trim().to_string();
                }
            }
        }
    }

    // Strip quality/audio keywords if still lingering
    let clean_title = JUNK_PATTERN_RE.replace_all(&text, "").to_string();
    let trimmed = clean_title.trim_matches(|c: char| {
        c == ' ' || c == '-' || c == ':' || c == '[' || c == ']' || c == '(' || c == ')' || c == '#'
    });
    let final_clean = WHITESPACE_RE.replace_all(trimmed, " ").trim().to_string();

    if final_clean.is_empty() {
        (raw_title.trim().to_string(), year)
    } else {
        (final_clean, year)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_messy_telegram_release() {
        let raw = "@KCFilmss - The Greatest of All Time 2024 Dual Audio 1080p.mkv";
        let (title, year) = sanitize_movie_query(raw);
        assert_eq!(title, "The Greatest of All Time");
        assert_eq!(year, Some(2024));
    }

    #[test]
    fn test_sanitize_with_brackets_and_size() {
        let raw = "Inception [1080p] [1.5 GB].mp4";
        let (title, year) = sanitize_movie_query(raw);
        assert_eq!(title, "Inception");
        assert_eq!(year, None);
    }

    #[test]
    fn test_sanitize_year_in_title_keep_start() {
        let raw = "1917 2019 1080p BluRay";
        let (title, year) = sanitize_movie_query(raw);
        assert_eq!(title, "1917");
        assert_eq!(year, Some(2019));
    }

    #[test]
    fn test_sanitize_watermarks_and_separators() {
        let raw = "www.TamilBlasters.vip - Leo.2023.Malayalam.ORG.720p.HD.AVC.AAC.mkv";
        let (title, year) = sanitize_movie_query(raw);
        assert_eq!(title, "Leo");
        assert_eq!(year, Some(2023));
    }
}
