# Graph Report - Cineforge  (2026-09-23)

## Corpus Check
- 70 files · ~49,545 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .css 5, (none) 4, .example 2)

## Summary
- 683 nodes · 1350 edges · 35 communities (31 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 49 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0226de25`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models/__init__.py
- AiQueryInterpretation
- App.jsx
- TmdbService
- TestCacheService
- ._get_client
- TestTmdbMetadataService
- MediaCompatibilityService
- package.json
- telethon_compat.py
- subtitle_service.py
- TestAiService
- Cineforge Backend
- TestAuthEndpointsAndService
- Cineforge Master Architecture & Implementation Roadmap (TODO)
- api/cache.py
- Settings
- export_session.py
- TestStreamerBotIntegration
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- AuthService
- SearchAggregatorService
- api/search.py
- TelegramService
- services/telegram.py
- _get_supabase_client
- get
- get_my_profile
- scratch_cineby_components.md
- MediaWaiter

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `SearchCandidate` - 19 edges
3. `TmdbService` - 18 edges
4. `react` - 17 edges
5. `AiQueryInterpretation` - 15 edges
6. `CacheService` - 14 edges
7. `MovieMetadata` - 13 edges
8. `AiService` - 13 edges
9. `TrendingMoviesResponse` - 12 edges
10. `MediaCompatibilityService` - 12 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py
- `TestDeliveryResponse` --uses--> `ButtonInfo`  [INFERRED]
  backend/app/models/delivery.py → backend/app/models/search.py
- `TelegramService` --uses--> `CandidateDeliveryRequest`  [INFERRED]
  backend/app/services/telegram.py → backend/app/models/delivery_flow.py

## Import Cycles
- None detected.

## Communities (35 total, 4 thin omitted)

### Community 0 - "models/__init__.py"
Cohesion: 0.17
Nodes (21): get_telegram_status(), get, post, Check if the Telethon user client is connected and authenticated without…, Development-only endpoint: Sends query to bot in private chat and returns…, Development-only endpoint: Registers an isolated waiter and waits for the next…, Development-only endpoint: Initiates Telegram deep link interaction with target…, test_delivery_flow() (+13 more)

### Community 1 - "AiQueryInterpretation"
Cohesion: 0.12
Nodes (26): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+18 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (57): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), DeliveryModal(), Footer(), HeroBanner(), fetchHeroMovies() (+49 more)

### Community 3 - "TmdbService"
Cohesion: 0.13
Nodes (16): TrendingMoviesResponse, Any, Search TMDb for movie metadata, fetch full details, credits, and videos.…, Extract a clean movie title and optional release year from messy release…, Parse raw TMDb API responses into MovieMetadata., Retrieve trending movies list for discovery carousel., Retrieve real, released popular movies from TMDb., Retrieve true top rated cinema masterpieces with high vote thresholds. (+8 more)

### Community 4 - "TestCacheService"
Cohesion: 0.14
Nodes (7): Verify GET /api/search returns is_cached=True on cache hit without calling…, Verify GET /api/cache/status returns status info., Verify search query normalization., When SUPABASE_URL is not set, cache operations must gracefully no-op., Verify conversion of Supabase database rows into SearchCandidate models., Verify caching of CineAI prompt interpretations., TestCacheService

### Community 5 - "._get_client"
Cohesion: 0.11
Nodes (16): Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Check connection and user authentication status., Development endpoint logic: Detailed search testing and button inspection in…, Extract detailed metadata from a Telegram media message without downloading., Automatically join a public channel or private invite link., Execute a delivery test for a given Telegram deep link with automated FSub…, Extract and normalize inline keyboard buttons from a Telegram message. (+8 more)

### Community 6 - "TestTmdbMetadataService"
Cohesion: 0.11
Nodes (9): GET /api/metadata/movie endpoint returns MovieMetadata model., GET /api/metadata/trending endpoint returns TrendingMoviesResponse model., Verify search_movie_suggestions parses TMDb search results into clean…, GET /api/search/suggestions returns 200 with suggestions list., Verify messy torrent/release filenames are cleanly sanitized., GET /api/metadata/status returns current configuration status., When TMDB_API_KEY is not set, service gracefully returns fallback metadata., Verify successful TMDb search, details, credits, and video parsing. (+1 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

### Community 8 - "package.json"
Cohesion: 0.08
Nodes (25): dependencies, lucide-react, react, react-dom, @supabase/supabase-js, devDependencies, oxlint, @types/react (+17 more)

### Community 9 - "telethon_compat.py"
Cohesion: 0.11
Nodes (15): Any, Isolated compatibility module for unmapped Telegram MTProto constructors.…, Compatibility implementation for Telegram constructor user#b1b8cc83 (Layer…, Idempotently registers constructor 0xb1b8cc83 into Telethon's type registry., register_telethon_compat(), UserCompatB1B8CC83, Verifies that serialization matches deserialization., Deserializes the exact byte structure captured from the live @Spoty_xbot error. (+7 more)

### Community 10 - "subtitle_service.py"
Cohesion: 0.05
Nodes (38): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+30 more)

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

### Community 17 - "export_session.py"
Cohesion: 0.33
Nodes (4): Utility to export existing cineforge_session.session into a…, os, telethon_sessions, telethon_sync

### Community 18 - "TestStreamerBotIntegration"
Cohesion: 0.33
Nodes (3): Verify _extract_streamer_links correctly extracts stream, watch, and download…, Verify POST /api/search/deliver returns valid stream and player URLs., TestStreamerBotIntegration

### Community 19 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 20 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 25 - "AuthService"
Cohesion: 0.19
Nodes (9): AuthService, get_current_user_optional(), get_current_user_required(), Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata., FastAPI dependency for optionally authenticated endpoints., FastAPI dependency for strictly protected endpoints. (+1 more)

### Community 26 - "SearchAggregatorService"
Cohesion: 0.15
Nodes (9): Any, Convert a candidate button into a rich SearchCandidate model., Aggregates paginated Telegram search candidate files, normalizes metadata, and…, Extract all candidate files and pagination metadata from a bot message., Deduplicate candidates preserving first-seen high-quality entries., Cluster candidate versions under canonical title keys., Rank candidates prioritizing browser compatibility, then quality, then size., Extract pagination indicators (e.g. 'Page: 1/220', 'Total Results: 2200',… (+1 more)

### Community 27 - "api/search.py"
Cohesion: 0.06
Nodes (58): asyncio, _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get, Concurrently resolve TMDb posters, backdrops, and ratings for movie title… (+50 more)

### Community 28 - "TelegramService"
Cohesion: 0.14
Nodes (12): Validate and resolve a selected search result reference for upcoming delivery., select_search_result(), SelectedResultRequest, SelectedResultResponse, Disconnect the Telegram client during application shutdown., Asynchronous callback when an incoming private message arrives., Validate and resolve a selected search result reference for delivery., Register global incoming message listeners on the Telethon client. (+4 more)

### Community 29 - "services/telegram.py"
Cohesion: 0.16
Nodes (12): deliver_candidate_file(), post, Trigger bot delivery for a candidate button, forward document to 'me', verify…, CandidateDeliveryRequest, CandidateDeliveryResponse, BaseModel, interactive_login(), Trigger bot delivery for a chosen candidate button, handle FSub gates, forward… (+4 more)

### Community 30 - "_get_supabase_client"
Cohesion: 0.23
Nodes (16): add_to_watchlist(), BulkSyncPayload, delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any, BaseModel (+8 more)

### Community 31 - "get"
Cohesion: 0.15
Nodes (13): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+5 more)

### Community 32 - "get_my_profile"
Cohesion: 0.33
Nodes (6): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user.

### Community 33 - "scratch_cineby_components.md"
Cohesion: 0.50
Nodes (3): FOOTER HTML, HEADER HTML, MAIN HTML (FIRST 8000 CHARS)

### Community 36 - "MediaWaiter"
Cohesion: 0.33
Nodes (4): MediaWaiter, Register an isolated waiter and await incoming media message with a timeout., Represents an isolated, asynchronous media waiter for a specific request., Future

## Knowledge Gaps
- **62 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 278 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `._get_client`, `MediaWaiter`, `services/telegram.py`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `api/search.py` to `models/__init__.py`, `SearchAggregatorService`, `TestCacheService`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `TestAiService` connect `TestAiService` to `AiQueryInterpretation`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _62 weakly-connected nodes found - possible documentation gaps or missing edges._