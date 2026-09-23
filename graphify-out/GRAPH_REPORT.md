# Graph Report - Cineforge  (2026-09-23)

## Corpus Check
- 70 files · ~47,279 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 2, .css 2)

## Summary
- 687 nodes · 1373 edges · 34 communities (30 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9a3a83ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CacheService
- config.py
- App.jsx
- tmdb.py
- TestCacheService
- TelegramService
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
- SearchCandidate
- normalize_search_query
- history.py
- search_movies
- get_my_profile
- movieTrivia.js

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `SearchCandidate` - 19 edges
3. `TmdbService` - 18 edges
4. `react` - 17 edges
5. `AiQueryInterpretation` - 15 edges
6. `CacheService` - 14 edges
7. `getTrendingMovies()` - 14 edges
8. `MovieMetadata` - 13 edges
9. `AiService` - 13 edges
10. `TrendingMoviesResponse` - 12 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `search_movies()` --uses--> `SearchCandidate`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `search_movies()` --uses--> `SearchPaginationInfo`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `search_movies()` --uses--> `SearchResponse`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py

## Import Cycles
- None detected.

## Communities (34 total, 4 thin omitted)

### Community 0 - "CacheService"
Cohesion: 0.16
Nodes (9): CacheService, Any, Check if CineAI already resolved this exact prompt/vague query., Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens., Save generated stream & player URLs in movies_cache for instant replay., Zero-latency cache service backed by Supabase PostgreSQL., Return cache health, status, and item counts., Check if Supabase caching is configured and enabled. (+1 more)

### Community 1 - "config.py"
Cohesion: 0.08
Nodes (36): ask_companion(), get_ai_status(), get_recommendations(), get, post, Returns the operational status and model configured for CineAI., Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural… (+28 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (60): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), DeliveryModal(), Footer(), DEFAULT_HERO_MOVIES, HeroBanner() (+52 more)

### Community 3 - "tmdb.py"
Cohesion: 0.08
Nodes (34): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+26 more)

### Community 4 - "TestCacheService"
Cohesion: 0.17
Nodes (6): Verify GET /api/search returns is_cached=True on cache hit without calling…, Verify GET /api/cache/status returns status info., When SUPABASE_URL is not set, cache operations must gracefully no-op., Verify conversion of Supabase database rows into SearchCandidate models., Verify caching of CineAI prompt interpretations., TestCacheService

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (29): MediaWaiter, Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response., Development endpoint logic: Detailed search testing and button inspection in… (+21 more)

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
Cohesion: 0.32
Nodes (4): AuthService, Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata.

### Community 26 - "SearchAggregatorService"
Cohesion: 0.29
Nodes (7): SearchPaginationInfo, Any, Convert a candidate button into a rich SearchCandidate model., Aggregates paginated Telegram search candidate files, normalizes metadata, and…, Extract all candidate files and pagination metadata from a bot message., Extract pagination indicators (e.g. 'Page: 1/220', 'Total Results: 2200',…, SearchAggregatorService

### Community 27 - "api/search.py"
Cohesion: 0.06
Nodes (65): asyncio, deliver_candidate_file(), find_title_versions(), get_search_suggestions(), get_search_ui(), get, post, Targeted search refinement: discovers all versions (1080p, 720p, MP4, MKV) of a… (+57 more)

### Community 28 - "SearchCandidate"
Cohesion: 0.29
Nodes (4): SearchCandidate, Deduplicate candidates preserving first-seen high-quality entries., Cluster candidate versions under canonical title keys., Rank candidates prioritizing browser compatibility, then quality, then size.

### Community 29 - "normalize_search_query"
Cohesion: 0.33
Nodes (4): normalize_search_query(), Persist newly discovered Telegram candidates into Supabase movies_cache., Normalize query for consistent database indexing (lowercase, stripped, single…, Verify search query normalization.

### Community 30 - "history.py"
Cohesion: 0.28
Nodes (16): add_to_watchlist(), BulkSyncPayload, delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any, BaseModel (+8 more)

### Community 31 - "search_movies"
Cohesion: 0.40
Nodes (5): _enrich_groups_with_metadata(), Any, Concurrently resolve TMDb posters, backdrops, and ratings for movie title…, Send a search query to the Telegram bot, aggregate candidates across pages,…, search_movies()

### Community 32 - "get_my_profile"
Cohesion: 0.33
Nodes (6): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user.

### Community 33 - "movieTrivia.js"
Cohesion: 0.40
Nodes (3): CINEMA_CALIBRATION_STEPS, CURATED_TRIVIA, GENERIC_TRIVIA_TEMPLATES

## Knowledge Gaps
- **63 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+58 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 280 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `CacheService`, `config.py`, `TestCacheService`, `SearchAggregatorService`, `api/search.py`, `normalize_search_query`, `search_movies`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `TestAiService` connect `TestAiService` to `config.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _63 weakly-connected nodes found - possible documentation gaps or missing edges._