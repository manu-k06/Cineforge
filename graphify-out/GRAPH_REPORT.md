# Graph Report - Cineforge  (2026-10-01)

## Corpus Check
- 77 files · ~100,736 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .bat 3, .example 2)

## Summary
- 781 nodes · 1586 edges · 26 communities (22 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3578c653`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SearchCandidate
- App.jsx
- tmdb.py
- AuthService
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
- Settings
- CineforgeTrayApp
- update_public_profile
- .oxlintrc.json
- React + Vite
- vercel.json
- rules/graphify.md
- workflows/graphify.md
- app/__init__.py
- TestStreamerBotIntegration
- main.py
- history.py

## God Nodes (most connected - your core abstractions)
1. `TelegramService` - 28 edges
2. `resolveApiBase()` - 22 edges
3. `SearchCandidate` - 20 edges
4. `react` - 19 edges
5. `TmdbService` - 18 edges
6. `CineforgeTrayApp` - 18 edges
7. `lucide-react` - 16 edges
8. `AiQueryInterpretation` - 15 edges
9. `WatchHistoryProvider()` - 15 edges
10. `getOptimizedImageUrl()` - 15 edges

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

## Communities (26 total, 4 thin omitted)

### Community 0 - "SearchCandidate"
Cohesion: 0.05
Nodes (30): SearchCandidate, CacheService, normalize_search_query(), Any, Persist newly discovered Telegram candidates into Supabase movies_cache., Check if CineAI already resolved this exact prompt/vague query., Normalize query for consistent database indexing (lowercase, stripped, single…, Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens. (+22 more)

### Community 2 - "App.jsx"
Cohesion: 0.06
Nodes (83): App(), AuthModal(), AvatarPickerModal(), ContinueWatchingRail(), DeliveryModal(), Footer(), HeroBanner(), fetchHeroMovies() (+75 more)

### Community 3 - "tmdb.py"
Cohesion: 0.05
Nodes (42): discover_movies(), get_metadata_status(), get_movie_metadata(), get_popular_movies(), get_top_rated_movies(), get_trending_movies(), get, Check if TMDb API integration is configured and available. (+34 more)

### Community 4 - "AuthService"
Cohesion: 0.19
Nodes (9): AuthService, get_current_user_optional(), get_current_user_required(), Any, Service for validating Supabase JWT tokens and retrieving user profiles., Verify Supabase JWT token and return authenticated user metadata., FastAPI dependency for optionally authenticated endpoints., FastAPI dependency for strictly protected endpoints. (+1 more)

### Community 5 - "TelegramService"
Cohesion: 0.07
Nodes (29): MediaWaiter, Any, Targeted title search refinement: discovers all versions (1080p, 720p, MP4,…, Trigger bot delivery for a chosen candidate button, handle FSub gates, forward…, Disconnect the Telegram client during application shutdown., Check connection and user authentication status., Extract stream_url, watch_url, and download_url from Streamer Bot response., Development endpoint logic: Detailed search testing and button inspection in… (+21 more)

### Community 6 - "api/search.py"
Cohesion: 0.05
Nodes (77): asyncio, get_cache_status(), get, Returns whether Supabase caching is active, along with total cached movies and…, _consolidate_title_groups(), deliver_candidate_file(), _enrich_groups_with_metadata(), find_title_versions() (+69 more)

### Community 7 - "MediaCompatibilityService"
Cohesion: 0.07
Nodes (17): MediaCompatibilityService, Any, Detects container tokens in title or button text using bounded word boundaries., Determines whether a media file is natively browser-playable or requires an…, Convenience boolean check., Ranks a list of SearchResultItem objects. Prioritizes: 1. Browser-compatible…, Centralized service to evaluate browser media compatibility and rank search…, Extracts container extension strictly from file suffix to prevent substring… (+9 more)

### Community 8 - "package.json"
Cohesion: 0.07
Nodes (27): dependencies, lucide-react, react, react-dom, react-router-dom, @supabase/supabase-js, devDependencies, oxlint (+19 more)

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
Cohesion: 0.18
Nodes (10): 🏗️ Architecture & Data Flow Overview, Cineforge Master Architecture & Implementation Roadmap (TODO), 📋 Phase 1: CineAI Intelligence & Query Refinement Engine, 📋 Phase 2: Metadata Enrichment (TMDb / IMDb API Integration), 📋 Phase 3: Supabase Persistence & Zero-Latency Stream Caching, 📋 Phase 4: User Authentication (Login & Sign Up), 📋 Phase 5: User Watch History & Watchlist ("Continue Watching"), 📋 Phase 6: Subtitle Extraction & WebVTT Streaming (+2 more)

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

### Community 30 - "TestStreamerBotIntegration"
Cohesion: 0.33
Nodes (3): Verify _extract_streamer_links correctly extracts stream, watch, and download…, Verify POST /api/search/deliver returns valid stream and player URLs., TestStreamerBotIntegration

### Community 34 - "main.py"
Cohesion: 0.06
Nodes (50): api_route, argparse, AsyncClient, ask_companion(), get_ai_status(), get_recommendations(), get, post (+42 more)

### Community 39 - "history.py"
Cohesion: 0.27
Nodes (17): add_to_watchlist(), BulkSyncPayload, clear_all_watch_history(), delete_watch_history(), _get_supabase_client(), get_watch_history(), get_watchlist(), Any (+9 more)

## Knowledge Gaps
- **66 isolated node(s):** `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components`, `name` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 318 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelegramService` connect `TelegramService` to `api/search.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `SearchCandidate` connect `SearchCandidate` to `main.py`, `api/search.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `TelegramService` (e.g. with `CandidateDeliveryRequest` and `CandidateDeliveryResponse`) actually correct?**
  _`TelegramService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SearchCandidate` (e.g. with `search_movies()` and `CacheService`) actually correct?**
  _`SearchCandidate` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugins`, `react/rules-of-hooks` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SearchCandidate` be split into smaller, more focused modules?**
  _Cohesion score 0.052597402597402594 - nodes in this community are weakly interconnected._
- **Should `App.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.059248809733733025 - nodes in this community are weakly interconnected._