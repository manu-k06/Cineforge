# Graph Report - Cineforge  (2026-09-22)

## Corpus Check
- 64 files · ~40,755 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 2, .css 2)

## Summary
- 641 nodes · 1235 edges · 32 communities (28 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 49 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5db1de10`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api/search.py
- AiQueryInterpretation
- App.jsx
- TmdbService
- CacheService
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
- export_session.py
- TestStreamerBotIntegration
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- TestTmdbMetadataService
- services/auth.py
- config.py
- TestCacheService
- AiService
- AuthService
- get_ai_status

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `SearchCandidate` - 19 edges
3. `TmdbService` - 18 edges
4. `AiQueryInterpretation` - 15 edges
5. `CacheService` - 14 edges
6. `react` - 14 edges
7. `MovieMetadata` - 13 edges
8. `AiService` - 13 edges
9. `TrendingMoviesResponse` - 12 edges
10. `MediaCompatibilityService` - 12 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `AiService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/ai_service.py → backend/app/models/ai.py
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py
- `AiService` --uses--> `AiRecommendationItem`  [INFERRED]
  backend/app/services/ai_service.py → backend/app/models/ai.py

## Import Cycles
- None detected.

## Communities (32 total, 4 thin omitted)

### Community 0 - "api/search.py"
Cohesion: 0.05
Nodes (73): asyncio, deliver_candidate_file(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any, get (+65 more)

### Community 1 - "AiQueryInterpretation"
Cohesion: 0.23
Nodes (16): ask_companion(), get_recommendations(), post, Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural…, Ask trivia, plot questions, or lore about a specific movie/show., refine_query(), AiCompanionAskRequest (+8 more)

### Community 2 - "App.jsx"
Cohesion: 0.09
Nodes (39): App(), AuthModal(), DeliveryModal(), HeroBanner(), fetchHeroMovies(), MovieCard(), MovieGrid(), fetchAllRails() (+31 more)

### Community 3 - "TmdbService"
Cohesion: 0.08
Nodes (33): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+25 more)

### Community 4 - "CacheService"
Cohesion: 0.14
Nodes (12): CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens., Save generated stream & player URLs in movies_cache for instant replay. (+4 more)

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (29): MediaWaiter, Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response., Development endpoint logic: Detailed search testing and button inspection in… (+21 more)

### Community 6 - "subtitle_service.py"
Cohesion: 0.09
Nodes (28): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+20 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

### Community 8 - "package.json"
Cohesion: 0.08
Nodes (25): dependencies, lucide-react, react, react-dom, @supabase/supabase-js, devDependencies, oxlint, @types/react (+17 more)

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
Cohesion: 0.18
Nodes (10): 🏗️ Architecture & Data Flow Overview, Cineforge Master Architecture & Implementation Roadmap (TODO), 📋 Phase 1: CineAI Intelligence & Query Refinement Engine, 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), 📋 Phase 3: Supabase Persistence & Zero-Latency Stream Caching, 📋 Phase 4: User Authentication (Login & Sign Up), 📋 Phase 5: User Watch History & Watchlist ("Continue Watching"), 📋 Phase 6: Subtitle Extraction & WebVTT Streaming (+2 more)

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

### Community 25 - "TestTmdbMetadataService"
Cohesion: 0.11
Nodes (9): GET /api/metadata/movie endpoint returns MovieMetadata model., GET /api/metadata/trending endpoint returns TrendingMoviesResponse model., Verify search_movie_suggestions parses TMDb search results into clean…, GET /api/search/suggestions returns 200 with suggestions list., Verify messy torrent/release filenames are cleanly sanitized., GET /api/metadata/status returns current configuration status., When TMDB_API_KEY is not set, service gracefully returns fallback metadata., Verify successful TMDb search, details, credits, and video parsing. (+1 more)

### Community 26 - "services/auth.py"
Cohesion: 0.15
Nodes (14): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user., lifespan(), get_current_user_optional() (+6 more)

### Community 27 - "config.py"
Cohesion: 0.24
Nodes (10): health_check(), get, root_redirect(), contextlib, fastapi_middleware_cors, fastapi_testclient, json, pydantic_settings (+2 more)

### Community 28 - "TestCacheService"
Cohesion: 0.14
Nodes (7): Verify GET /api/search returns is_cached=True on cache hit without calling…, Verify GET /api/cache/status returns status info., Verify search query normalization., When SUPABASE_URL is not set, cache operations must gracefully no-op., Verify conversion of Supabase database rows into SearchCandidate models., Verify caching of CineAI prompt interpretations., TestCacheService

### Community 29 - "AiService"
Cohesion: 0.23
Nodes (6): AiService, Produce curated movie/series recommendations matching a mood, theme, or prompt., CineAI service utilizing Google Gemini for query refinement, thematic…, Answer lore, plot breakdown, trivia, or cast questions about a specific…, Heuristic check to bypass LLM for queries that are clearly exact titles to…, Interpret, correct typos, and resolve natural language/vague descriptions into…

### Community 30 - "AuthService"
Cohesion: 0.32
Nodes (4): AuthService, Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata.

### Community 31 - "get_ai_status"
Cohesion: 0.67
Nodes (3): get_ai_status(), get, Returns the operational status and model configured for CineAI.

## Knowledge Gaps
- **55 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 270 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `api/search.py` to `config.py`, `CacheService`, `TestCacheService`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `TestAiService` connect `TestAiService` to `config.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TmdbService` (e.g. with `CastMember` and `MovieMetadata`) actually correct?**
  _`TmdbService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `AiQueryInterpretation` (e.g. with `refine_query()` and `AiService`) actually correct?**
  _`AiQueryInterpretation` has 3 INFERRED edges - model-reasoned connections that need verification._