# Cineforge Master Architecture & Implementation Roadmap (TODO)

This document tracks all planned backend enhancements, data integrations, and features for Cineforge—combining the original roadmap items with the newly discussed **CineAI**, **Supabase (Caching & Auth)**, and **24/7 Production Deployment**.

---

## 🏗️ Architecture & Data Flow Overview

```
                          ┌────────────────────────────┐
                          │   Frontend (React + Vite)  │
                          │   Hosted on Vercel         │
                          └─────────────┬──────────────┘
                                        │
                         User Auth JWT  │  Search & Stream Requests
                                        ▼
                          ┌────────────────────────────┐
                          │    FastAPI Backend API     │
                          │    (Render / Cloud VPS)    │
                          └──────┬──────────────┬──────┘
                                 │              │
             1. Check Cache /    │              │ 2. Smart Query Refiner
             Save Streams / Auth │              │    (Typo / Vague Plot Search)
                                 ▼              ▼
                    ┌──────────────────┐  ┌───────────────────┐
                    │     Supabase     │  │   Google Gemini   │
                    │  (Postgres DB &  │  │   AI Engine       │
                    │   Supabase Auth) │  │  (gemini-1.5/2.0) │
                    └──────────────────┘  └───────────────────┘
                                 │
                     Cache Miss  │
                                 ▼
                    ┌───────────────────────────┐
                    │  Telegram Bot (Spoty Bot) │
                    │  & Stream Delivery Engine │
                    └───────────────────────────┘
```

---

## 📋 Phase 1: CineAI Intelligence & Query Refinement Engine

**Goal**: Transform search from literal string matching into an intelligent, semantic movie discovery engine. Fix typos, resolve vague plot descriptions to exact movie titles, and provide thematic recommendations & movie companion lore.

- [x] **1.1. AI Service Setup (`app/services/ai_service.py`)**
  - Integrated Google Gemini API using `httpx` async REST client with `gemini-2.0-flash-lite`.
  - Added `GEMINI_API_KEY`, `GEMINI_MODEL`, `AI_SEARCH_ENABLED` to `app/config.py` and `.env.example`.
- [x] **1.2. Natural Language & Vague Plot Resolution**
  - Function: `resolve_movie_query(user_query: str) -> AiQueryInterpretation`.
  - Resolves vague descriptions (*"the movie where cooper goes into a wormhole"*) $\rightarrow$ `{"canonical_title": "Interstellar", "year": "2014", "search_query": "Interstellar 2014"}`.
  - Fixes typos and variations (*"shawshank redemtion"* $\rightarrow$ *"The Shawshank Redemption"*).
- [x] **1.3. Smart Query Router (Latency & Cost Optimization)**
  - Fast-path heuristic bypass for already specific queries to maintain near-zero latency.
  - Seamless fallback to raw search if unconfigured or network errors occur.
- [x] **1.4. Thematic & Mood Recommendations**
  - Endpoint: `POST /api/ai/recommend`.
  - Takes natural requests (*"Give me mind-bending thrillers like Shutter Island"*) and outputs structured movie titles ready to stream.
- [x] **1.5. CineAI Companion & Trivia**
  - Endpoint: `POST /api/ai/ask`.
  - Interactive movie trivia, plot explanations, and character lore.
- [x] **1.6. AI Search UI Indicator**
  - Frontend search banner: glassmorphic **"✨ CineAI"** badge showing canonical title identification and option to revert to exact search.

---

## 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)

**Goal**: Automatically fetch authoritative poster backdrops, synopses, cast lists with profile headshots, directors, IMDb ratings, and user reviews for any searched title.

- [x] **2.1. TMDb Service (`app/services/tmdb.py`)**
  - Query TMDb Search & Details API (`/search/movie`, `/movie/{id}?append_to_response=credits,videos`) to resolve:
    - Official high-res posters and 4K backdrop banners.
    - Full cast list (actor name, character name, profile headshot URLs).
    - Crew: Directors, release year, runtime, genres.
    - Verified IMDb / TMDb ratings and vote counts.
    - Official YouTube trailers.
- [x] **2.2. Metadata Caching & Zero-Crash Fallbacks**
  - In-memory TTL cache (`ttl=24h`) keyed by sanitized movie title and year.
  - Automatic fallback generator ensures smooth streaming even without an API key.
- [x] **2.3. Frontend Movie Details & Card Enrichment**
  - Upgraded `MovieCard` with official HD posters and rating stars.
  - Connected `WatchPage` with dynamic 4K backdrop, synopsis, and full cast carousel.
  - Added live Trending discovery integration in `App.jsx`.


---

## 📋 Phase 3: Supabase Persistence & Zero-Latency Stream Caching

**Goal**: Store resolved movie search results, metadata, and generated stream URLs in Supabase so users get instant (<50ms) search responses without hitting Telegram bot rate limits.

- [x] **3.1. Supabase Project & Python Integration**
  - Installed `supabase>=2.0.0` in `backend/requirements.txt`.
  - Added `SUPABASE_URL`, `SUPABASE_KEY`, and `CACHE_ENABLED` to `backend/app/config.py`.
- [x] **3.2. Database Schema Setup (Supabase SQL)**
  - Created schema for `movies_cache` and `ai_query_cache`.
- [x] **3.3. Cache-First Search Pipeline in Backend (`app/api/search.py`)**
  - Check `ai_query_cache` first to bypass LLM calls on repeated vague queries.
  - Check `movies_cache` for normalized title/query matches before querying Telegram bot.
  - **Hit**: Return cached results immediately (<50ms) with `is_cached: true`.
  - **Miss**: Query `@Spoty_xbot`, deliver stream links, and asynchronously write discovered candidates into `movies_cache`.
- [x] **3.4. Stream URL Freshness & Persistence Handling**
  - Save generated `stream_url` and `watch_url` into `movies_cache` upon candidate delivery.
- [x] **3.5. Frontend Cache Indicator**
  - Added `⚡ Supabase Cache Hit` badge in `App.jsx`.

---

## 📋 Phase 4: User Authentication (Login & Sign Up)

**Goal**: Enable personal accounts so users can log in, access their personal watchlist, and continue watching across devices.

- [x] **4.1. Supabase Auth Client in Frontend**
  - Install `@supabase/supabase-js` in `frontend/package.json`.
  - Create `src/services/supabaseClient.js` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- [x] **4.2. Authentication Context (`src/context/AuthContext.jsx`)**
  - Global React context for auth state (`user`, `session`, `loading`, `signIn`, `signUp`, `signOut`).
- [x] **4.3. Auth UI Modal (`src/components/AuthModal.jsx`)**
  - Modern modal matching Cineforge dark aesthetics.
  - Tab 1: **Sign In** (Email + Password).
  - Tab 2: **Create Account** (Full Name, Email, Password).
  - 1-Click **Google OAuth Login**.
- [x] **4.4. Navbar User Profile Badge**
  - Update `src/components/Navbar.jsx` to show avatar, username, and "Sign Out" dropdown when logged in; or "Sign In" button when guest.
- [x] **4.5. Backend JWT Verification Middleware**
  - FastAPI dependency to verify `Authorization: Bearer <token>` from Supabase for protected endpoints (`/api/auth/me`).

---

## 📋 Phase 5: User Watch History & Watchlist ("Continue Watching")

**Goal**: Deliver a streaming service experience where user progress is saved in real-time.

- [ ] **5.1. Watch History & Watchlist Tables in Supabase**
  ```sql
  -- User Watch History
  CREATE TABLE public.user_watch_history (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
      movie_id UUID REFERENCES public.movies_cache(id) ON DELETE CASCADE,
      title TEXT NOT NULL,
      poster_url TEXT,
      stream_url TEXT NOT NULL,
      progress_seconds FLOAT NOT NULL DEFAULT 0,
      duration_seconds FLOAT NOT NULL DEFAULT 0,
      completed BOOLEAN DEFAULT FALSE,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      UNIQUE(user_id, movie_id)
  );

  -- User Watchlist / Favorites
  CREATE TABLE public.user_watchlist (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
      movie_id UUID REFERENCES public.movies_cache(id) ON DELETE CASCADE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      UNIQUE(user_id, movie_id)
  );
  ```
- [ ] **5.2. Playback Progress Syncing**
  - On `WatchPage.jsx`, sync playback position every 10 seconds to `user_watch_history`.
- [ ] **5.3. "Continue Watching" UI Section**
  - Fetch active watch history on the Homepage and render a progress bar on resumed movie thumbnails.
- [ ] **5.4. Watchlist Toggle Buttons**
  - Add "+ Watchlist" button on movie detail cards and watch page.

---

## 📋 Phase 6: Subtitle Extraction & WebVTT Streaming

**Goal**: Deliver soft subtitles (`.srt`, `.ass`, `.vtt`) extracted directly from Telegram MKV/MP4 files or OpenSubtitles to the browser player.

- [x] **6.1. Embedded Subtitle Detection**
  - Inspect media streams via `ffprobe` to detect all embedded soft subtitle tracks with ISO 639-1 language codes.
- [x] **6.2. WebVTT Streaming Endpoint**
  - Endpoint: `GET /api/subtitles/tracks` for discovery, `GET /api/subtitles/embedded` for on-the-fly extraction to standard WebVTT, and `GET /api/subtitles/demo.vtt` for playback sync testing.
- [x] **6.3. External Subtitles & In-Memory Caching**
  - In-memory cache for parsed WebVTT text and discovered tracks with configurable TTL (`SUBTITLE_CACHE_TTL`), plus OpenSubtitles API configuration readiness.
- [x] **6.4. Player Subtitle Selector & Timing Sync UI**
  - Closed captions button (`Captions` / `CaptionsOff`), glassmorphic popover track picker, dynamic `<track>` mounting, and live timing sync offset controls (`-0.5s` / `+0.5s` / `Reset`).

---

## 📋 Phase 7: Bot Channel & Multi-Source Search Fallback

**Goal**: Support fallback to additional Telegram file search channels/bots if `@Spoty_xbot` experiences rate limits, maintenance, or downtime.

- [ ] **7.1. Secondary Search Provider Adapter**
  - Modular provider interface in `app/services/telegram.py` supporting multiple search bots/channels.
- [ ] **7.2. Automatic Health Check & Failover**
  - If `@Spoty_xbot` times out or fails after 2 retries, fail over to configured fallback channel/bot automatically.

---

## 📋 Phase 8: 24/7 Production Deployment & Stability

**Goal**: Keep both backend and frontend running 24/7 without manual intervention.

- [x] **8.1. Stateless Cloud Telegram Authentication**
  - Added `TELEGRAM_STRING_SESSION` support so Render/cloud hosts don't require an ephemeral `.session` disk file.
  - Added `backend/export_session.py` to export local session strings.
- [x] **8.2. Docker & Native Python Support on Render**
  - Created `backend/Dockerfile` and `render.yaml`.
  - Configured Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] **8.3. 24/7 Free Tier Keep-Alive**
  - Set up external ping (e.g. UptimeRobot / Cron-Job) hitting `/health` every 10 minutes to prevent Render free instance sleep.
- [ ] **8.4. Frontend Vercel Environment Configuration**
  - Point `VITE_API_BASE_URL` in Vercel to production Render domain.
