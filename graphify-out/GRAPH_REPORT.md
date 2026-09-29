# Graph Report - Cineforge  (2026-09-29)

## Corpus Check
- 74 files · ~51,702 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 756 nodes · 1510 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8fa2fd61`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SearchCandidate
- main.py
- App.jsx
- TmdbService
- api/search.py
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
- api/__init__.py
- Settings
- CineforgeTrayApp
- TestStreamerBotIntegration
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- SubtitleService
- subtitle_service.py
- logging
- TestTmdbMetadataService
- services/telegram.py
- history.py
- get
- search_aggregator.py
- movieTrivia.js
- AiQueryInterpretation
- typing
- AuthService
- ._register_event_handlers
- proxy_to_streamer
- get_my_profile
- test_telegram_search
- get_ai_status

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `SearchCandidate` - 20 edges
3. `resolveApiBase()` - 19 edges
4. `TmdbService` - 18 edges
5. `react` - 18 edges
6. `CineforgeTrayApp` - 18 edges
7. `AiQueryInterpretation` - 15 edges
8. `getTrendingMovies()` - 15 edges
9. `CacheService` - 14 edges
10. `MovieMetadata` - 13 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `search_movies()` --uses--> `SearchCandidate`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `search_movies()` --uses--> `SearchPaginationInfo`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `select_search_result()` --uses--> `SelectedResultRequest`  [INFERRED]
  backend/app/api/search.py → backend/app/models/delivery.py

## Import Cycles
- None detected.

## Communities (42 total, 4 thin omitted)

### Community 0 - "SearchCandidate"
Cohesion: 0.05
Nodes (31): SearchCandidate, SearchPaginationInfo, CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single… (+23 more)

### Community 1 - "main.py"
Cohesion: 0.21
Nodes (12): health_check(), get, root_redirect(), contextlib, fastapi_middleware_cors, fastapi_testclient, httpx, json (+4 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (68): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), CINEMA_TRIVIA, DeliveryModal(), Footer(), DEFAULT_HERO_MOVIES (+60 more)

### Community 3 - "TmdbService"
Cohesion: 0.13
Nodes (16): TrendingMoviesResponse, Any, Construct fallback metadata when TMDb is not configured or title is not found., Search TMDb for movie metadata, fetch full details, credits, and videos.…, Extract a clean movie title and optional release year from messy release…, Parse raw TMDb API responses into MovieMetadata., Retrieve trending movies strictly available on OTT / Digital streaming., Retrieve real, released popular movies from TMDb with confirmed OTT/Digital… (+8 more)

### Community 4 - "api/search.py"
Cohesion: 0.12
Nodes (25): deliver_candidate_file(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get, post (+17 more)

### Community 5 - "TelegramService"
Cohesion: 0.11
Nodes (19): Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Development endpoint logic: Detailed search testing and button inspection in…, Extract detailed metadata from a Telegram media message without downloading., Register an isolated waiter and await incoming media message with a timeout., Automatically join a public channel or private invite link. (+11 more)

### Community 6 - "models/__init__.py"
Cohesion: 0.18
Nodes (21): post, Development-only endpoint: Registers an isolated waiter and waits for the next…, Development-only endpoint: Initiates Telegram deep link interaction with target…, test_delivery_flow(), test_media_detection(), DeepLinkInfo, MediaMetadata, parse_telegram_deep_link() (+13 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

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
Nodes (10): Verify POST /api/ai/recommend endpoint., Verify POST /api/ai/ask companion endpoint., Verify GET /api/ai/status returns status and model info., Verify GET /api/search response contains ai_interpretation field., When GEMINI_API_KEY is unset, refine_movie_query returns clean fallback., Queries with explicit year e.g. 'Inception 2010' should bypass LLM call., Verify parsing of Gemini JSON output for vague plot searches., Verify POST /api/ai/refine endpoint. (+2 more)

### Community 12 - "Cineforge Backend"
Cohesion: 0.11
Nodes (17): 1. Create a Streaming Session, 1. Navigate to the Backend Directory, 2. Create & Activate Virtual Environment, 2. View Real-Time Buffering Health & Viability Metrics, 3. Install Dependencies, 3. View Probed Metadata & Compatibility (B7), 4. Configure `.env`, 4. Stream Byte Range (B6 Regression) (+9 more)

### Community 13 - "TestAuthEndpointsAndService"
Cohesion: 0.17
Nodes (6): Verify GET /api/auth/status returns status., GET /api/auth/me should return 401 when no token is supplied., GET /api/auth/me should return 401 when token verification fails., GET /api/auth/me should return user profile with valid Bearer token., Verify auth_service parses Supabase GoTrue user response correctly., TestAuthEndpointsAndService

### Community 14 - "Cineforge Master Architecture & Implementation Roadmap (TODO)"
Cohesion: 0.20
Nodes (9): 🏗️ Architecture & Data Flow Overview, Cineforge Master Architecture & Implementation Roadmap (TODO), 📋 Phase 1: CineAI Intelligence & Query Refinement Engine, 📋 Phase 3: Supabase Persistence & Zero-Latency Stream Caching, 📋 Phase 4: User Authentication (Login & Sign Up), 📋 Phase 5: User Watch History & Watchlist ("Continue Watching"), 📋 Phase 6: Subtitle Extraction & WebVTT Streaming, 📋 Phase 7: Bot Channel & Multi-Source Search Fallback (+1 more)

### Community 15 - "api/__init__.py"
Cohesion: 0.24
Nodes (8): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase.

### Community 16 - "Settings"
Cohesion: 0.43
Nodes (3): Settings, BaseSettings, field_validator

### Community 17 - "CineforgeTrayApp"
Cohesion: 0.06
Nodes (30): atexit, Utility to export existing cineforge_session.session into a…, Image, Menu, os, pathlib, pil, pystray (+22 more)

### Community 18 - "TestStreamerBotIntegration"
Cohesion: 0.33
Nodes (3): Verify _extract_streamer_links correctly extracts stream, watch, and download…, Verify POST /api/search/deliver returns valid stream and player URLs., TestStreamerBotIntegration

### Community 19 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 20 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 25 - "SubtitleService"
Cohesion: 0.18
Nodes (12): BaseModel, SubtitleTrack, clean_movie_title(), Scrub messy release strings, telegram handles, bot prefixes, and rip tags to…, Service for discovering, downloading, and streaming multi-language WebVTT…, Generate high-quality synchronized sample WebVTT for playback testing…, Query Stremio OpenSubtitles v3 CDN API for verified movie subtitles. Bypasses…, Query OpenSubtitles REST API for verified movie subtitles. Supports lookup by… (+4 more)

### Community 26 - "subtitle_service.py"
Cohesion: 0.22
Nodes (11): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., SubtitleTrackListResponse (+3 more)

### Community 27 - "logging"
Cohesion: 0.15
Nodes (15): argparse, lifespan(), get_current_user_optional(), get_current_user_required(), FastAPI dependency for optionally authenticated endpoints., FastAPI dependency for strictly protected endpoints., main(), publish_tunnel_url() (+7 more)

### Community 28 - "TestTmdbMetadataService"
Cohesion: 0.11
Nodes (9): GET /api/metadata/movie endpoint returns MovieMetadata model., GET /api/metadata/trending endpoint returns TrendingMoviesResponse model., Verify search_movie_suggestions parses TMDb search results into clean…, GET /api/search/suggestions returns 200 with suggestions list., Verify messy torrent/release filenames are cleanly sanitized., GET /api/metadata/status returns current configuration status., When TMDB_API_KEY is not set, service gracefully returns fallback metadata., Verify successful TMDb search, details, credits, and video parsing. (+1 more)

### Community 29 - "services/telegram.py"
Cohesion: 0.15
Nodes (9): interactive_login(), MediaWaiter, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Extract stream_url, watch_url, and download_url from Streamer Bot response., CLI utility for one-time interactive Telegram login., Represents an isolated, asynchronous media waiter for a specific request., Future, telethon (+1 more)

### Community 30 - "history.py"
Cohesion: 0.28
Nodes (16): add_to_watchlist(), BulkSyncPayload, delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any, BaseModel (+8 more)

### Community 31 - "get"
Cohesion: 0.15
Nodes (13): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+5 more)

### Community 32 - "search_aggregator.py"
Cohesion: 0.26
Nodes (7): asyncio, MediaCompatibilityResult, Services package for Cineforge backend., dataclasses, hashlib, re, time

### Community 33 - "movieTrivia.js"
Cohesion: 0.40
Nodes (3): CINEMA_CALIBRATION_STEPS, CURATED_TRIVIA, GENERIC_TRIVIA_TEMPLATES

### Community 34 - "AiQueryInterpretation"
Cohesion: 0.14
Nodes (22): ask_companion(), get_recommendations(), post, Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural…, Ask trivia, plot questions, or lore about a specific movie/show., refine_query(), AiCompanionAskRequest (+14 more)

### Community 35 - "typing"
Cohesion: 0.47
Nodes (6): CastMember, CrewMember, MovieMetadata, BaseModel, pydantic, typing

### Community 36 - "AuthService"
Cohesion: 0.32
Nodes (4): AuthService, Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata.

### Community 37 - "._register_event_handlers"
Cohesion: 0.25
Nodes (5): Asynchronous callback when an incoming private message arrives., Register global incoming message listeners on the Telethon client., Connect the Telegram client during application startup., on_private_message(), TelegramClient

### Community 38 - "proxy_to_streamer"
Cohesion: 0.29
Nodes (6): api_route, AsyncClient, get_streamer_client(), proxy_to_streamer(), Request, Proxy video streaming and download range requests to local Go FileStreamBot…

### Community 39 - "get_my_profile"
Cohesion: 0.33
Nodes (6): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user.

### Community 40 - "test_telegram_search"
Cohesion: 0.40
Nodes (5): get_telegram_status(), get, Check if the Telethon user client is connected and authenticated without…, Development-only endpoint: Sends query to bot in private chat and returns…, test_telegram_search()

### Community 41 - "get_ai_status"
Cohesion: 0.67
Nodes (3): get_ai_status(), get, Returns the operational status and model configured for CineAI.

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 316 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `._register_event_handlers`, `api/search.py`, `services/telegram.py`, `models/__init__.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `search_aggregator.py`, `main.py`, `typing`, `api/search.py`, `models/__init__.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SearchCandidate` be split into smaller, more focused modules?**
  _Cohesion score 0.05263157894736842 - nodes in this community are weakly interconnected._