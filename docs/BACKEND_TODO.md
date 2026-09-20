# Cineforge Backend Architecture & Roadmap

This document keeps track of planned backend enhancements, data integrations, and features to be implemented following the frontend UI conversion of the StreamVibe template.

---

## 📋 1. Metadata Enrichment (TMDb / IMDb API Integration)
- **Goal**: Automatically fetch authoritative poster backdrops, synopses, cast lists with profile headshots, directors, IMDb ratings, and user reviews for any searched title.
- **Implementation**:
  - Service: `app/services/tmdb.py`
  - Integration: When `GET /api/search?q=...` runs, query TMDb Search API (`https://api.themoviedb.org/3/search/multi`) to resolve:
    - Official poster and 4K backdrop banners.
    - Full cast list (actor name, character name, profile image path).
    - Crew: Director, writers, composer.
    - Verified IMDb / TMDb ratings and vote counts.
    - Curated reviews with user avatars.
  - Cache: In-memory LRU or Redis cache (`ttl=24h`) keyed by sanitized movie name and year.

---

## 📋 2. Subtitle Extraction & WebVTT Streaming
- **Goal**: Deliver soft subtitles (`.srt`, `.ass`, `.vtt`) extracted directly from Telegram MKV/MP4 files to the browser player.
- **Implementation**:
  - Many files delivered by Spoty Bot contain embedded subtitle tracks.
  - Endpoint: `GET /api/stream/{file_id}/subtitles/{track_id}.vtt`
  - Streamer Bot / TG-FileStreamBot can be queried or parsed for embedded subtitle streams, or external OpenSubtitles API can provide matched subtitles.

---

## 📋 3. User Playback Progress & Watch History
- **Goal**: Allow users to resume watching where they left off ("Continue Watching" row on Home).
- **Implementation**:
  - Model: `PlaybackHistory` (user_id, file_id, title, duration, current_timestamp, completed_percentage).
  - Endpoints:
    - `POST /api/user/progress`
    - `GET /api/user/history`

---

## 📋 4. CineAI Backend (Movie Companion & Smart Discovery)
- **Goal**: Natural language search & scene-by-scene companion.
- **Implementation**:
  - Service: `app/services/ai_service.py` using Google Gemini API (`gemini-1.5-flash`).
  - Endpoints:
    - `POST /api/ai/ask`: Movie trivia, plot explanation, character lore.
    - `POST /api/ai/recommend`: Natural language recommendation engine that outputs query terms fed to `@Spoty_xbot`.

---

## 📋 5. Bot Channel & Multi-Source Search
- **Goal**: Support fallback to additional Telegram file search channels/bots if `@Spoty_xbot` experiences rate limits or downtime.
