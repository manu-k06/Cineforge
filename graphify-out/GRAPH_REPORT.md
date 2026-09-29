# Graph Report - Cineforge  (2026-09-29)

## Corpus Check
- 74 files · ~51,060 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 753 nodes · 1502 edges · 32 communities (27 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f5a617ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SearchCandidate
- main.py
- App.jsx
- tmdb.py
- api/search.py
- TelegramService
- subtitle_service.py
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
- TestStreamerBotIntegration
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- SubtitleService
- api/subtitles.py
- publish_tunnel.py
- .download_and_convert_vtt
- history.py
- movieTrivia.js
- config.py

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `SearchCandidate` - 19 edges
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
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py
- `TelegramService` --uses--> `SelectedResultRequest`  [INFERRED]
  backend/app/services/telegram.py → backend/app/models/delivery.py

## Import Cycles
- None detected.

## Communities (32 total, 5 thin omitted)

### Community 0 - "SearchCandidate"
Cohesion: 0.06
Nodes (29): SearchCandidate, CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens. (+21 more)

### Community 1 - "main.py"
Cohesion: 0.14
Nodes (15): api_route, AsyncClient, get_streamer_client(), health_check(), lifespan(), proxy_to_streamer(), get, Request (+7 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (68): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), CINEMA_TRIVIA, DeliveryModal(), Footer(), DEFAULT_HERO_MOVIES (+60 more)

### Community 3 - "tmdb.py"
Cohesion: 0.05
Nodes (42): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+34 more)

### Community 4 - "api/search.py"
Cohesion: 0.07
Nodes (62): asyncio, deliver_candidate_file(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get (+54 more)

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (29): MediaWaiter, Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response., Development endpoint logic: Detailed search testing and button inspection in… (+21 more)

### Community 6 - "subtitle_service.py"
Cohesion: 0.24
Nodes (9): Convert SubRip (.srt) text format to W3C WebVTT (.vtt) format. Normalizes line…, srt_to_vtt(), fastapi_testclient, gzip, io, unittest, unittest_mock, urllib_parse (+1 more)

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
Nodes (11): Verify direct UTF-8 SRT download from Stremio CDN and conversion to WebVTT., Verify OpenSubtitles gzip decompression, conversion, and in-memory caching., GET /api/subtitles/tracks returns 200 with track list and demo fallback., Verify SRT format is converted to compliant WebVTT format., GET /api/subtitles/vtt returns 200 with text/vtt media type., GET /api/subtitles/demo.vtt returns 200 with text/vtt content., Verify BOM stripping and empty content handling., Verify demo WebVTT contains movie title and valid cue blocks. (+3 more)

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

### Community 15 - "api/cache.py"
Cohesion: 0.27
Nodes (8): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase.

### Community 16 - "Settings"
Cohesion: 0.43
Nodes (3): Settings, BaseSettings, field_validator

### Community 17 - "CineforgeTrayApp"
Cohesion: 0.07
Nodes (26): atexit, Image, Menu, pathlib, pil, pystray, subprocess, sys (+18 more)

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
Cohesion: 0.26
Nodes (9): SubtitleTrack, clean_movie_title(), Scrub messy release strings, telegram handles, bot prefixes, and rip tags to…, Service for discovering, downloading, and streaming multi-language WebVTT…, Query Stremio OpenSubtitles v3 CDN API for verified movie subtitles. Bypasses…, Query OpenSubtitles REST API for verified movie subtitles. Supports lookup by…, Query community Yify Subtitles repository for verified SRT tracks. Supports…, Aggregate clean subtitle tracks from OpenSubtitles and community sources.… (+1 more)

### Community 26 - "api/subtitles.py"
Cohesion: 0.25
Nodes (9): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+1 more)

### Community 27 - "publish_tunnel.py"
Cohesion: 0.33
Nodes (6): argparse, main(), publish_tunnel_url(), Utility to publish live tunnel URL and server status into Supabase. Enables the…, Upsert the active backend URL and online status to Supabase server_status table., datetime

### Community 30 - "history.py"
Cohesion: 0.09
Nodes (32): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user., add_to_watchlist(), BulkSyncPayload (+24 more)

### Community 33 - "movieTrivia.js"
Cohesion: 0.40
Nodes (3): CINEMA_CALIBRATION_STEPS, CURATED_TRIVIA, GENERIC_TRIVIA_TEMPLATES

### Community 34 - "config.py"
Cohesion: 0.11
Nodes (27): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+19 more)

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 314 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `api/search.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SearchCandidate` be split into smaller, more focused modules?**
  _Cohesion score 0.055904961565338925 - nodes in this community are weakly interconnected._