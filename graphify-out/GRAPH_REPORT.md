# Graph Report - Cineforge  (2026-10-01)

## Corpus Check
- 77 files · ~102,271 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 787 nodes · 1611 edges · 35 communities (31 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d67ef2b3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CacheService
- services/telegram.py
- App.jsx
- TmdbService
- AuthService
- TelegramService
- models/__init__.py
- MediaCompatibilityService
- package.json
- telethon_compat.py
- subtitle_service.py
- TestAiService
- Cineforge Backend
- TestAuthEndpointsAndService
- Cineforge Master Architecture & Implementation Roadmap (TODO)
- typing
- Settings
- CineforgeTrayApp
- update_public_profile
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- api/search.py
- SearchAggregatorService
- DeliveryModal.jsx
- main.py
- TestStreamerBotIntegration
- api/__init__.py
- get
- proxy_to_streamer
- AiQueryInterpretation
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
- `select_search_result()` --uses--> `SelectedResultRequest`  [INFERRED]
  backend/app/api/search.py → backend/app/models/delivery.py
- `select_search_result()` --uses--> `SelectedResultResponse`  [INFERRED]
  backend/app/api/search.py → backend/app/models/delivery.py
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py

## Import Cycles
- None detected.

## Communities (35 total, 4 thin omitted)

### Community 0 - "CacheService"
Cohesion: 0.07
Nodes (19): CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens., Save generated stream & player URLs in movies_cache for instant replay. (+11 more)

### Community 1 - "services/telegram.py"
Cohesion: 0.15
Nodes (15): asyncio, deliver_candidate_file(), post, Request, Trigger bot delivery for a candidate button, forward document to 'me', verify…, Validate and resolve a selected search result reference for upcoming delivery., select_search_result(), CandidateDeliveryRequest (+7 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (81): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), AvatarPickerModal(), ContinueWatchingRail(), Footer(), HeroBanner(), fetchHeroMovies() (+73 more)

### Community 3 - "TmdbService"
Cohesion: 0.06
Nodes (25): TrendingMoviesResponse, Any, Construct fallback metadata when TMDb is not configured or title is not found., Search TMDb for movie metadata, fetch full details, credits, and videos.…, Extract a clean movie title and optional release year from messy release…, Parse raw TMDb API responses into MovieMetadata., Retrieve trending movies strictly available on OTT / Digital streaming., Retrieve real, released popular movies from TMDb with confirmed OTT/Digital… (+17 more)

### Community 4 - "AuthService"
Cohesion: 0.19
Nodes (9): AuthService, get_current_user_optional(), get_current_user_required(), Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata., FastAPI dependency for optionally authenticated endpoints., FastAPI dependency for strictly protected endpoints. (+1 more)

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (30): MediaWaiter, Any, Click pagination callback on an active search result message and accumulate…, Disconnect the Telegram client during application shutdown., Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response. (+22 more)

### Community 6 - "models/__init__.py"
Cohesion: 0.15
Nodes (24): get_telegram_status(), get, post, Check if the Telethon user client is connected and authenticated without…, Development-only endpoint: Sends query to bot in private chat and returns…, Development-only endpoint: Registers an isolated waiter and waits for the next…, Development-only endpoint: Initiates Telegram deep link interaction with target…, test_delivery_flow() (+16 more)

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

### Community 15 - "typing"
Cohesion: 0.17
Nodes (17): argparse, lifespan(), CastMember, CrewMember, MovieMetadata, BaseModel, main(), publish_tunnel_url() (+9 more)

### Community 16 - "Settings"
Cohesion: 0.43
Nodes (3): Settings, BaseSettings, field_validator

### Community 17 - "CineforgeTrayApp"
Cohesion: 0.06
Nodes (30): atexit, Utility to export existing cineforge_session.session into a…, Image, Menu, os, pathlib, pil, pystray (+22 more)

### Community 18 - "update_public_profile"
Cohesion: 0.17
Nodes (13): get_auth_status(), get_my_profile(), get_public_profile(), ProfileUpdatePayload, Any, BaseModel, get, patch (+5 more)

### Community 19 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 20 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 25 - "api/search.py"
Cohesion: 0.14
Nodes (26): _consolidate_title_groups(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get, Send a search query to the Telegram bot, aggregate candidates across pages,… (+18 more)

### Community 26 - "SearchAggregatorService"
Cohesion: 0.13
Nodes (10): Any, Convert a candidate button into a rich SearchCandidate model., Aggregates paginated Telegram search candidate files, normalizes metadata, and…, Extract all candidate files and pagination metadata from a bot message., Deduplicate candidates preserving first-seen high-quality entries., Cluster candidate versions under canonical title keys and sort by query…, Extract pagination indicators (e.g. 'Page: 1/220', 'Total Results: 2200',…, Sort title groups by relevance to query (exact match first, then prefix, etc.). (+2 more)

### Community 27 - "DeliveryModal.jsx"
Cohesion: 0.36
Nodes (6): DeliveryModal(), CINEMA_CALIBRATION_STEPS, CURATED_TRIVIA, GENERIC_TRIVIA_TEMPLATES, getMovieTrivia(), getMovieTriviaList()

### Community 28 - "main.py"
Cohesion: 0.22
Nodes (10): health_check(), get, root_redirect(), contextlib, fastapi_middleware_cors, fastapi_testclient, httpx, starlette_responses (+2 more)

### Community 29 - "TestStreamerBotIntegration"
Cohesion: 0.33
Nodes (3): Verify _extract_streamer_links correctly extracts stream, watch, and download…, Verify POST /api/search/deliver returns valid stream and player URLs., TestStreamerBotIntegration

### Community 30 - "api/__init__.py"
Cohesion: 0.24
Nodes (8): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase.

### Community 31 - "get"
Cohesion: 0.15
Nodes (13): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+5 more)

### Community 32 - "proxy_to_streamer"
Cohesion: 0.29
Nodes (6): api_route, AsyncClient, get_streamer_client(), proxy_to_streamer(), Request, Proxy video streaming and download range requests to local Go FileStreamBot…

### Community 34 - "AiQueryInterpretation"
Cohesion: 0.12
Nodes (26): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+18 more)

### Community 39 - "history.py"
Cohesion: 0.27
Nodes (17): add_to_watchlist(), BulkSyncPayload, clear_all_watch_history(), delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any (+9 more)

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 319 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `services/telegram.py`, `models/__init__.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `api/search.py` to `CacheService`, `SearchAggregatorService`, `main.py`, `models/__init__.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CacheService` be split into smaller, more focused modules?**
  _Cohesion score 0.07394957983193277 - nodes in this community are weakly interconnected._
- **Should `App.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06586712354844851 - nodes in this community are weakly interconnected._