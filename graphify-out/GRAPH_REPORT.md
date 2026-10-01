# Graph Report - Cineforge  (2026-10-01)

## Corpus Check
- 78 files · ~103,007 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 795 nodes · 1626 edges · 40 communities (36 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `203a5df5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- cache_service.py
- api/search.py
- App.jsx
- TmdbService
- AuthService
- TelegramService
- services/telegram.py
- MediaCompatibilityService
- package.json
- telethon_compat.py
- subtitle_service.py
- TestAiService
- Cineforge Backend
- TestAuthEndpointsAndService
- Cineforge Master Architecture & Implementation Roadmap (TODO)
- api/auth.py
- Settings
- CineforgeTrayApp
- update_public_profile
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- models/__init__.py
- SearchCandidate
- tray_app.py
- main.py
- TestStreamerBotIntegration
- pydantic
- typing
- proxy_to_streamer
- TestCacheService
- AiQueryInterpretation
- search_aggregator.py
- AiService
- test_telegram_search
- MediaWaiter
- history.py

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 29 edges
2. `resolveApiBase()` - 22 edges
3. `SearchCandidate` - 20 edges
4. `react` - 19 edges
5. `TmdbService` - 18 edges
6. `CineforgeTrayApp` - 18 edges
7. `WatchHistoryProvider()` - 17 edges
8. `lucide-react` - 16 edges
9. `AiQueryInterpretation` - 15 edges
10. `getTrendingMovies()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `search_movies()` --uses--> `SearchCandidate`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `select_search_result()` --uses--> `SelectedResultRequest`  [INFERRED]
  backend/app/api/search.py → backend/app/models/delivery.py
- `select_search_result()` --uses--> `SelectedResultResponse`  [INFERRED]
  backend/app/api/search.py → backend/app/models/delivery.py

## Import Cycles
- None detected.

## Communities (40 total, 4 thin omitted)

### Community 0 - "cache_service.py"
Cohesion: 0.14
Nodes (12): CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens., Save generated stream & player URLs in movies_cache for instant replay. (+4 more)

### Community 1 - "api/search.py"
Cohesion: 0.13
Nodes (17): deliver_candidate_file(), get_search_suggestions(), get_search_ui(), get, post, Request, Trigger bot delivery for a candidate button, forward document to 'me', verify…, Validate and resolve a selected search result reference for upcoming delivery. (+9 more)

### Community 2 - "App.jsx"
Cohesion: 0.06
Nodes (87): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), AvatarPickerModal(), ContinueWatchingRail(), DeliveryModal(), Footer(), HeroBanner() (+79 more)

### Community 3 - "TmdbService"
Cohesion: 0.07
Nodes (28): CastMember, MovieMetadata, BaseModel, TrendingMoviesResponse, Any, Construct fallback metadata when TMDb is not configured or title is not found., Search TMDb for movie metadata, fetch full details, credits, and videos.…, Extract a clean movie title and optional release year from messy release… (+20 more)

### Community 4 - "AuthService"
Cohesion: 0.32
Nodes (4): AuthService, Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata.

### Community 5 - "TelegramService"
Cohesion: 0.08
Nodes (25): Any, Click pagination callback on an active search result message and accumulate…, Disconnect the Telegram client during application shutdown., Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Check connection and user authentication status., Extract detailed metadata from a Telegram media message without downloading., Development endpoint logic: Detailed search testing and button inspection in…, Asynchronous callback when an incoming private message arrives. (+17 more)

### Community 6 - "services/telegram.py"
Cohesion: 0.20
Nodes (18): post, Development-only endpoint: Registers an isolated waiter and waits for the next…, Development-only endpoint: Initiates Telegram deep link interaction with target…, test_delivery_flow(), test_media_detection(), DeepLinkInfo, MediaMetadata, parse_telegram_deep_link() (+10 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

### Community 8 - "package.json"
Cohesion: 0.07
Nodes (28): dependencies, lucide-react, react, react-dom, react-router-dom, @supabase/supabase-js, devDependencies, oxlint (+20 more)

### Community 9 - "telethon_compat.py"
Cohesion: 0.11
Nodes (15): Any, Isolated compatibility module for unmapped Telegram MTProto constructors.…, Compatibility implementation for Telegram constructor user#b1b8cc83 (Layer…, Idempotently registers constructor 0xb1b8cc83 into Telethon's type registry., register_telethon_compat(), UserCompatB1B8CC83, Verifies that serialization matches deserialization., Deserializes the exact byte structure captured from the live @Spoty_xbot error. (+7 more)

### Community 10 - "subtitle_service.py"
Cohesion: 0.05
Nodes (37): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+29 more)

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

### Community 15 - "api/auth.py"
Cohesion: 0.16
Nodes (15): argparse, lifespan(), get_current_user_optional(), get_current_user_required(), FastAPI dependency for optionally authenticated endpoints., FastAPI dependency for strictly protected endpoints., main(), publish_tunnel_url() (+7 more)

### Community 16 - "Settings"
Cohesion: 0.43
Nodes (3): Settings, BaseSettings, field_validator

### Community 17 - "CineforgeTrayApp"
Cohesion: 0.10
Nodes (17): Image, Menu, CineforgeTrayApp, create_tray_icon(), Publish status to Supabase using publish_tunnel utility., Launch fsb.exe, backend uvicorn, and cloudflared tunnel with NO console windows., Continuously check tunnel URL and ensure processes remain healthy., Invoked when Cloudflare tunnel URL is established. (+9 more)

### Community 18 - "update_public_profile"
Cohesion: 0.17
Nodes (13): get_auth_status(), get_my_profile(), get_public_profile(), ProfileUpdatePayload, Any, BaseModel, get, patch (+5 more)

### Community 19 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 20 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 25 - "models/__init__.py"
Cohesion: 0.20
Nodes (16): _consolidate_title_groups(), _enrich_groups_with_metadata(), find_title_versions(), Any, Send a search query to the Telegram bot, aggregate candidates across pages,…, Concurrently resolve TMDb posters, backdrops, and ratings for movie title…, Targeted search refinement: discovers all versions (1080p, 720p, MP4, MKV) of a…, Merge title groups that share the exact same TMDb movie ID, guaranteeing only 1… (+8 more)

### Community 26 - "SearchCandidate"
Cohesion: 0.15
Nodes (11): SearchCandidate, Any, Convert a candidate button into a rich SearchCandidate model., Aggregates paginated Telegram search candidate files, normalizes metadata, and…, Extract all candidate files and pagination metadata from a bot message., Deduplicate candidates preserving first-seen high-quality entries., Cluster candidate versions under canonical title keys and sort by query…, Extract pagination indicators (e.g. 'Page: 1/220', 'Total Results: 2200',… (+3 more)

### Community 27 - "tray_app.py"
Cohesion: 0.09
Nodes (21): atexit, Utility to export existing cineforge_session.session into a…, main(), update_qr_files(), ctypes, os, pathlib, pil (+13 more)

### Community 28 - "main.py"
Cohesion: 0.21
Nodes (12): health_check(), get, root_redirect(), contextlib, fastapi_middleware_cors, fastapi_testclient, httpx, json (+4 more)

### Community 29 - "TestStreamerBotIntegration"
Cohesion: 0.33
Nodes (3): Verify _extract_streamer_links correctly extracts stream, watch, and download…, Verify POST /api/search/deliver returns valid stream and player URLs., TestStreamerBotIntegration

### Community 30 - "pydantic"
Cohesion: 0.21
Nodes (9): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase. (+1 more)

### Community 31 - "typing"
Cohesion: 0.17
Nodes (15): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+7 more)

### Community 32 - "proxy_to_streamer"
Cohesion: 0.29
Nodes (6): api_route, AsyncClient, get_streamer_client(), proxy_to_streamer(), Request, Proxy video streaming and download range requests to local Go FileStreamBot…

### Community 33 - "TestCacheService"
Cohesion: 0.14
Nodes (7): Verify GET /api/search returns is_cached=True on cache hit without calling…, Verify GET /api/cache/status returns status info., Verify search query normalization., When SUPABASE_URL is not set, cache operations must gracefully no-op., Verify conversion of Supabase database rows into SearchCandidate models., Verify caching of CineAI prompt interpretations., TestCacheService

### Community 34 - "AiQueryInterpretation"
Cohesion: 0.19
Nodes (19): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+11 more)

### Community 35 - "search_aggregator.py"
Cohesion: 0.19
Nodes (9): asyncio, MediaCompatibilityResult, Services package for Cineforge backend., interactive_login(), CLI utility for one-time interactive Telegram login., dataclasses, hashlib, re (+1 more)

### Community 36 - "AiService"
Cohesion: 0.23
Nodes (6): AiService, Produce curated movie/series recommendations matching a mood, theme, or prompt., CineAI service utilizing Google Gemini for query refinement, thematic…, Answer lore, plot breakdown, trivia, or cast questions about a specific…, Heuristic check to bypass LLM for queries that are clearly exact titles to…, Interpret, correct typos, and resolve natural language/vague descriptions into…

### Community 37 - "test_telegram_search"
Cohesion: 0.40
Nodes (5): get_telegram_status(), get, Check if the Telethon user client is connected and authenticated without…, Development-only endpoint: Sends query to bot in private chat and returns…, test_telegram_search()

### Community 38 - "MediaWaiter"
Cohesion: 0.50
Nodes (3): MediaWaiter, Represents an isolated, asynchronous media waiter for a specific request., Future

### Community 39 - "history.py"
Cohesion: 0.27
Nodes (17): add_to_watchlist(), BulkSyncPayload, clear_all_watch_history(), delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any (+9 more)

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 320 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`, `services/telegram.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `CineforgeTrayApp` connect `CineforgeTrayApp` to `tray_app.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `cache_service.py`, `api/search.py`, `TestCacheService`, `search_aggregator.py`, `models/__init__.py`, `main.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `cache_service.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13852813852813853 - nodes in this community are weakly interconnected._