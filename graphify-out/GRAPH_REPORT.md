# Graph Report - Cineforge  (2026-09-30)

## Corpus Check
- 74 files · ~54,735 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 761 nodes · 1535 edges · 32 communities (28 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94eb8aa3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SearchCandidate
- main.py
- App.jsx
- tmdb.py
- AiService
- TelegramService
- api/search.py
- MediaCompatibilityService
- package.json
- telethon_compat.py
- subtitle_service.py
- TestAiService
- Cineforge Backend
- TestAuthEndpointsAndService
- Cineforge Master Architecture & Implementation Roadmap (TODO)
- pydantic
- Settings
- CineforgeTrayApp
- TestStreamerBotIntegration
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- config.py
- publish_tunnel.py
- history.py
- DeliveryModal.jsx
- AiQueryInterpretation
- services/auth.py
- get_ai_status

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `resolveApiBase()` - 21 edges
3. `SearchCandidate` - 20 edges
4. `TmdbService` - 18 edges
5. `react` - 18 edges
6. `CineforgeTrayApp` - 18 edges
7. `getTrendingMovies()` - 17 edges
8. `AiQueryInterpretation` - 15 edges
9. `lucide-react` - 15 edges
10. `getOptimizedImageUrl()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `MovieCard()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/MovieCard.jsx
- `📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration)` --references--> `WatchPage()`  [INFERRED]
  docs/BACKEND_TODO.md → frontend/src/components/WatchPage.jsx
- `search_movies()` --uses--> `SearchCandidate`  [INFERRED]
  backend/app/api/search.py → backend/app/models/search.py
- `AiService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/ai_service.py → backend/app/models/ai.py
- `CacheService` --uses--> `AiQueryInterpretation`  [INFERRED]
  backend/app/services/cache_service.py → backend/app/models/ai.py

## Import Cycles
- None detected.

## Communities (32 total, 4 thin omitted)

### Community 0 - "SearchCandidate"
Cohesion: 0.05
Nodes (30): SearchCandidate, CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens. (+22 more)

### Community 1 - "main.py"
Cohesion: 0.14
Nodes (15): api_route, AsyncClient, get_streamer_client(), health_check(), lifespan(), proxy_to_streamer(), get, Request (+7 more)

### Community 2 - "App.jsx"
Cohesion: 0.07
Nodes (69): 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), App(), AuthModal(), ContinueWatchingRail(), Footer(), DEFAULT_HERO_MOVIES, HeroBanner(), fetchHeroMovies() (+61 more)

### Community 3 - "tmdb.py"
Cohesion: 0.05
Nodes (42): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+34 more)

### Community 4 - "AiService"
Cohesion: 0.23
Nodes (6): AiService, Produce curated movie/series recommendations matching a mood, theme, or prompt., CineAI service utilizing Google Gemini for query refinement, thematic…, Answer lore, plot breakdown, trivia, or cast questions about a specific…, Heuristic check to bypass LLM for queries that are clearly exact titles to…, Interpret, correct typos, and resolve natural language/vague descriptions into…

### Community 5 - "TelegramService"
Cohesion: 0.09
Nodes (24): Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Development endpoint logic: Detailed search testing and button inspection in…, Extract detailed metadata from a Telegram media message without downloading., Asynchronous callback when an incoming private message arrives., Register an isolated waiter and await incoming media message with a timeout. (+16 more)

### Community 6 - "api/search.py"
Cohesion: 0.06
Nodes (71): asyncio, _consolidate_title_groups(), deliver_candidate_file(), _enrich_groups_with_metadata(), find_title_versions(), get_search_suggestions(), get_search_ui(), Any (+63 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

### Community 8 - "package.json"
Cohesion: 0.07
Nodes (26): dependencies, lucide-react, react, react-dom, @supabase/supabase-js, devDependencies, oxlint, @types/react (+18 more)

### Community 9 - "telethon_compat.py"
Cohesion: 0.11
Nodes (15): Any, Isolated compatibility module for unmapped Telegram MTProto constructors.…, Compatibility implementation for Telegram constructor user#b1b8cc83 (Layer…, Idempotently registers constructor 0xb1b8cc83 into Telethon's type registry., register_telethon_compat(), UserCompatB1B8CC83, Verifies that serialization matches deserialization., Deserializes the exact byte structure captured from the live @Spoty_xbot error. (+7 more)

### Community 10 - "subtitle_service.py"
Cohesion: 0.05
Nodes (37): get_demo_vtt(), get_subtitle_tracks(), get_vtt_track(), get, Search and return clean, multi-language subtitle tracks via API providers…, Fetch subtitle payload from provider, convert to standard W3C WebVTT, and…, Return synchronized test WebVTT captions., BaseModel (+29 more)

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

### Community 15 - "pydantic"
Cohesion: 0.24
Nodes (9): get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, CachedCandidateRecord, CacheStatsResponse, BaseModel, Operational statistics for Cineforge Supabase cache., Database representation of a cached movie candidate in Supabase. (+1 more)

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

### Community 25 - "config.py"
Cohesion: 0.40
Nodes (5): fastapi_testclient, json, pydantic_settings, unittest, unittest_mock

### Community 27 - "publish_tunnel.py"
Cohesion: 0.33
Nodes (6): argparse, main(), publish_tunnel_url(), Utility to publish live tunnel URL and server status into Supabase. Enables the…, Upsert the active backend URL and online status to Supabase server_status table., datetime

### Community 30 - "history.py"
Cohesion: 0.28
Nodes (16): add_to_watchlist(), BulkSyncPayload, delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any, BaseModel (+8 more)

### Community 33 - "DeliveryModal.jsx"
Cohesion: 0.36
Nodes (6): DeliveryModal(), CINEMA_CALIBRATION_STEPS, CURATED_TRIVIA, GENERIC_TRIVIA_TEMPLATES, getMovieTrivia(), getMovieTriviaList()

### Community 34 - "AiQueryInterpretation"
Cohesion: 0.23
Nodes (16): ask_companion(), get_recommendations(), post, Interprets vague descriptions, corrects typos, and outputs a canonical search…, Generate movie or show recommendations matching a theme, mood, or natural…, Ask trivia, plot questions, or lore about a specific movie/show., refine_query(), AiCompanionAskRequest (+8 more)

### Community 39 - "services/auth.py"
Cohesion: 0.12
Nodes (16): get_auth_status(), get_my_profile(), Any, get, Check if Supabase Auth is configured on the backend., Retrieve profile information for the currently authenticated user., AuthService, get_current_user_optional() (+8 more)

### Community 41 - "get_ai_status"
Cohesion: 0.67
Nodes (3): get_ai_status(), get, Returns the operational status and model configured for CineAI.

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 315 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `config.py`, `api/search.py`?**
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
  _Cohesion score 0.052597402597402594 - nodes in this community are weakly interconnected._