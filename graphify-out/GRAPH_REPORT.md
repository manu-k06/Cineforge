# Graph Report - Cineforge  (2026-09-30)

## Corpus Check
- 75 files · ~57,309 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 766 nodes · 1545 edges · 33 communities (29 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1fd6c26a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CacheService
- main.py
- App.jsx
- TmdbService
- AuthService
- TelegramService
- models/__init__.py
- MediaCompatibilityService
- package.json
- telethon_compat.py
- TestSubtitleServiceAndEndpoints
- TestAiService
- Cineforge Backend
- TestAuthEndpointsAndService
- Cineforge Master Architecture & Implementation Roadmap (TODO)
- api/cache.py
- Settings
- CineforgeTrayApp
- api/auth.py
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- SearchCandidate
- SubtitleService
- api/search.py
- subtitle_service.py
- api/metadata.py
- proxy_to_streamer
- AiQueryInterpretation
- history.py

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `resolveApiBase()` - 21 edges
3. `SearchCandidate` - 20 edges
4. `TmdbService` - 18 edges
5. `react` - 18 edges
6. `CineforgeTrayApp` - 18 edges
7. `AiQueryInterpretation` - 15 edges
8. `lucide-react` - 15 edges
9. `getOptimizedImageUrl()` - 15 edges
10. `CacheService` - 14 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py
- `TelegramService` --uses--> `SelectedResultRequest`  [INFERRED]
  backend/app/services/telegram.py → backend/app/models/delivery.py
- `TelegramService` --uses--> `SelectedResultResponse`  [INFERRED]
  backend/app/services/telegram.py → backend/app/models/delivery.py

## Import Cycles
- None detected.

## Communities (33 total, 4 thin omitted)

### Community 0 - "CacheService"
Cohesion: 0.07
Nodes (19): CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens., Save generated stream & player URLs in movies_cache for instant replay. (+11 more)

### Community 1 - "main.py"
Cohesion: 0.22
Nodes (10): health_check(), lifespan(), get, root_redirect(), publish_tunnel_url(), Upsert the active backend URL and online status to Supabase server_status table., contextlib, fastapi_middleware_cors (+2 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (73): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), DeliveryModal(), Footer(), HeroBanner(), fetchHeroMovies() (+65 more)

### Community 3 - "TmdbService"
Cohesion: 0.06
Nodes (29): CastMember, CrewMember, MovieMetadata, BaseModel, TrendingMoviesResponse, Any, Construct fallback metadata when TMDb is not configured or title is not found., Search TMDb for movie metadata, fetch full details, credits, and videos.… (+21 more)

### Community 4 - "AuthService"
Cohesion: 0.32
Nodes (4): AuthService, Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata.

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (29): MediaWaiter, Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response., Development endpoint logic: Detailed search testing and button inspection in… (+21 more)

### Community 6 - "models/__init__.py"
Cohesion: 0.09
Nodes (40): deliver_candidate_file(), post, Request, Trigger bot delivery for a candidate button, forward document to 'me', verify…, Validate and resolve a selected search result reference for upcoming delivery., select_search_result(), get_telegram_status(), get (+32 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.06
Nodes (24): MediaCompatibilityResult, MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search… (+16 more)

### Community 8 - "package.json"
Cohesion: 0.07
Nodes (26): dependencies, lucide-react, react, react-dom, @supabase/supabase-js, devDependencies, oxlint, @types/react (+18 more)

### Community 9 - "telethon_compat.py"
Cohesion: 0.11
Nodes (15): Any, Isolated compatibility module for unmapped Telegram MTProto constructors.…, Compatibility implementation for Telegram constructor user#b1b8cc83 (Layer…, Idempotently registers constructor 0xb1b8cc83 into Telethon's type registry., register_telethon_compat(), UserCompatB1B8CC83, Verifies that serialization matches deserialization., Deserializes the exact byte structure captured from the live @Spoty_xbot error. (+7 more)

### Community 10 - "TestSubtitleServiceAndEndpoints"
Cohesion: 0.09
Nodes (13): Convert SubRip (.srt) text format to W3C WebVTT (.vtt) format. Normalizes line…, srt_to_vtt(), Verify direct UTF-8 SRT download from Stremio CDN and conversion to WebVTT., Verify OpenSubtitles gzip decompression, conversion, and in-memory caching., GET /api/subtitles/tracks returns 200 with track list and demo fallback., Verify SRT format is converted to compliant WebVTT format., GET /api/subtitles/vtt returns 200 with text/vtt media type., GET /api/subtitles/demo.vtt returns 200 with text/vtt content. (+5 more)

### Community 11 - "TestAiService"
Cohesion: 0.12
Nodes (10): patch, Verify POST /api/ai/recommend endpoint., Verify POST /api/ai/ask companion endpoint., Verify GET /api/ai/status returns status and model info., Verify GET /api/search response contains ai_interpretation field., When GEMINI_API_KEY is unset, refine_movie_query returns clean fallback., Queries with explicit year e.g. 'Inception 2010' should bypass LLM call., Verify parsing of Gemini JSON output for vague plot searches. (+2 more)

### Community 12 - "Cineforge Backend"
Cohesion: 0.11
Nodes (17): 1. Create a Streaming Session, 1. Navigate to the Backend Directory, 2. Create & Activate Virtual Environment, 2. View Real-Time Buffering Health & Viability Metrics, 3. Install Dependencies, 3. View Probed Metadata & Compatibility (B7), 4. Configure `.env`, 4. Stream Byte Range (B6 Regression) (+9 more)

### Community 13 - "TestAuthEndpointsAndService"
Cohesion: 0.17
Nodes (6): Verify GET /api/auth/status returns status., GET /api/auth/me should return 401 when no token is supplied., GET /api/auth/me should return 401 when token verification fails., GET /api/auth/me should return user profile with valid Bearer token., Verify auth_service parses Supabase GoTrue user response correctly., TestAuthEndpointsAndService

### Community 14 - "Cineforge Master Architecture & Implementation Roadmap (TODO)"
Cohesion: 0.20
Nodes (9): 🏗️ Architecture & Data Flow Overview, Cineforge Master Architecture & Implementation Roadmap (TODO), 📋 Phase 1: CineAI Intelligence & Query Refinement Engine, 📋 Phase 3: Supabase Persistence & Zero-Latency Stream Caching, 📋 Phase 4: User Authentication (Login & Sign Up), 📋 Phase 5: User Watch History & Watchlist ("Continue Watching"), 📋 Phase 6: Subtitle Extraction & WebVTT Streaming, 📋 Phase 7: Bot Channel & Multi-Source Search Fallback (+1 more)

### Community 15 - "api/cache.py"
Cohesion: 0.27
Nodes (8): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase.

### Community 16 - "Settings"
Cohesion: 0.43
Nodes (3): Settings, BaseSettings, field_validator

### Community 17 - "CineforgeTrayApp"
Cohesion: 0.07
Nodes (26): atexit, Image, Menu, pathlib, pil, pystray, subprocess, sys (+18 more)

### Community 18 - "api/auth.py"
Cohesion: 0.13
Nodes (20): get_auth_status(), get_my_profile(), get_public_profile(), ProfileUpdatePayload, Any, BaseModel, get, patch (+12 more)

### Community 19 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 20 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 25 - "SearchCandidate"
Cohesion: 0.08
Nodes (29): _consolidate_title_groups(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get, Send a search query to the Telegram bot, aggregate candidates across pages,… (+21 more)

### Community 26 - "SubtitleService"
Cohesion: 0.18
Nodes (10): clean_movie_title(), Scrub messy release strings, telegram handles, bot prefixes, and rip tags to…, Service for discovering, downloading, and streaming multi-language WebVTT…, Generate high-quality synchronized sample WebVTT for playback testing…, Query Stremio OpenSubtitles v3 CDN API for verified movie subtitles. Bypasses…, Query OpenSubtitles REST API for verified movie subtitles. Supports lookup by…, Query community Yify Subtitles repository for verified SRT tracks. Supports…, Download subtitle payload (gzip or zip archive), extract SRT, convert to… (+2 more)

### Community 27 - "api/search.py"
Cohesion: 0.23
Nodes (12): argparse, asyncio, main(), Utility to publish live tunnel URL and server status into Supabase. Enables the…, datetime, fastapi_responses, hashlib, logging (+4 more)

### Community 28 - "subtitle_service.py"
Cohesion: 0.21
Nodes (13): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+5 more)

### Community 29 - "api/metadata.py"
Cohesion: 0.18
Nodes (13): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+5 more)

### Community 30 - "proxy_to_streamer"
Cohesion: 0.29
Nodes (6): api_route, AsyncClient, get_streamer_client(), proxy_to_streamer(), Request, Proxy video streaming and download range requests to local Go FileStreamBot…

### Community 34 - "AiQueryInterpretation"
Cohesion: 0.08
Nodes (32): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+24 more)

### Community 39 - "history.py"
Cohesion: 0.28
Nodes (16): add_to_watchlist(), BulkSyncPayload, delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any, BaseModel (+8 more)

## Knowledge Gaps
- **64 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 316 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `models/__init__.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `CacheService`, `AiQueryInterpretation`, `api/search.py`, `models/__init__.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _64 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CacheService` be split into smaller, more focused modules?**
  _Cohesion score 0.07394957983193277 - nodes in this community are weakly interconnected._