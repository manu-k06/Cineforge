# Cineforge Learning & Architectural Log

## Project Goal
Migrate Cineforge from a multi-process Python/FastAPI backend to an installable Windows desktop application powered by **Tauri 2** and **Rust**, while preserving the existing React frontend, the Go media streamer (`TG-FileStreamBot`), and ensuring high-trust security for all user credentials.

---

## Completed Milestones

### Stage 1: Tauri 2 Desktop Shell
- Initialized Tauri 2 shell around existing React 19 + Vite 8 frontend.
- Retained full web app compatibility for browser builds.

### Stage 2: Embedded Rust Backend Foundation
- Embedded an Axum HTTP API service running inside the Tauri process on loopback (`127.0.0.1`).
- Dynamically allocates an ephemeral port to avoid port collisions with legacy backends.
- Built-in graceful shutdown coupled to the Tauri application lifecycle.

### Stage 3.1: TMDb Metadata Port & Edge Function Proxy
- Implemented TMDb metadata routes in Rust matching the FastAPI contract (`/status`, `/movie`, `/trending`, `/popular`, `/top-rated`, `/discover`).
- Prepared a secured Supabase Edge Function (`supabase/functions/tmdb-proxy/index.ts`) for cloud secret storage.
- Removed shared API keys from frontend and desktop assets.
- Restrictive CORS configured for desktop origins.

### Stage 4.1: User Telegram Account Connection & Encryption at Rest
- **Client Architecture**: Chose `grammers` (by Lonami, author of Telethon) for pure Rust MTProto v2 client communication without requiring heavy C++ TDLib runtimes or Python daemons.
- **Account Model**: Cineforge registered app credentials (`api_id` and `api_hash`) identify the client application. Each user authorizes their *own* personal account.
- **QR Code Flow**: Invokes `auth.exportLoginToken`, encodes `tg://login?token=<b64>`, renders vector SVG inline via `qrcode` crate, and polls for mobile approval.
- **Fallback Verification**: Supports international phone numbers, verification codes, and 2FA cloud password authorization (`check_password`).
- **Data Protection at Rest**: User session keys are encrypted strictly on the user's PC using **Windows DPAPI** (`CryptProtectData`) to `%APPDATA%\Cineforge\telegram_session.enc`. Never exposed to Supabase, logs, or `localStorage`.
- **Developer Session Isolation**: Developer's existing `backend/cineforge_session.session` is completely isolated and untouched.
- **Disconnect & Wipe**: Explicit disconnect action revokes the MTProto session with Telegram (`auth.logOut`), wipes the local encrypted file, and purges in-memory keys.
- **Desktop UI**: `TelegramConnectModal.jsx` and status badge in `Navbar.jsx` with automatic polling and state management.

### Desktop Bug Fixes & Resiliency Hardening
- **Regression 1: Telegram SenderPoolRunner dropped & DC Migration**:
  - *Root Cause*: `SenderPool::new` creates a runner (`pool.runner`) and a handle (`pool.handle`). In the initial implementation, `runner.run()` was not driven by an active Tokio task and `pool` went out of scope, dropping the receiver channel. When in-flight network requests were sent via the client handle, the runner was dropped, triggering `request error: dropped: SenderPoolRunner was dropped during retry at send`.
  - *Fix*: Spawned `runner.run()` inside a long-lived Tokio task stored on `MtprotoTelegramBackend`, with graceful abort on client drop. Handled Telegram Data Center (DC) migration (`auth.loginTokenMigrateTo` -> `client.invoke_in_dc(dc_id, &ImportLoginToken)`).
  - *Session Persistence*: Implemented `DpapiSession` implementing the `grammers_session::Session` trait. Stores permanent MTProto auth keys and DC options into encrypted DPAPI storage surviving app restarts.
  - *Credentials Safety*: Enforced zero hardcoded credentials and zero logging of sensitive tokens. Credentials are read strictly from `.env` or system environment.
- **Regression 2: Missing Home Hero Content & Regional ISP DNS Poisoning**:
  - *Root Cause 1 (DNS Hijacking)*: In many regions (e.g. Reliance Jio in India), ISPs poison/sinkhole DNS queries for `api.themoviedb.org` to an ISP block/blackhole IP (`49.44.79.236`). Connecting to port 443 on that IP dropped packets, resulting in `reqwest::Error: TimedOut` after 6 seconds. `fetch_upstream_json` failed, causing `get_trending_movies` to return an empty array `[]`.
  - *Root Cause 2 (Packaged Desktop Config Discovery)*: `load_env_files()` in `config.rs` only searched `backend/.env` and `%APPDATA%\Cineforge\.env`, omitting the installed application directory (`<exe_dir>/.env`), current working directory, and `frontend/.env`.
  - *Root Cause 3 (Hero Layout Void)*: When `movies.length === 0`, `HeroBanner.jsx` rendered inside `.home-hero` with `clamp(620px, 88vh, 780px)` and `min-height: 600px`, creating a barren black void that consumed nearly the entire screen.
  - *Fix 1 (Resilient CloudFront IP Resolution)*: Configured `reqwest::Client` in `TmdbService::new` with explicit `resolve` overrides for authentic AWS CloudFront Anycast IPs (`3.175.86.67`, `3.175.86.103`, `3.175.86.50`). TMDb metadata now resolves and streams 20 real movies with full artwork in ~0.95 seconds.
  - *Fix 2 (Multi-Source Config Resolution)*: Enhanced `config::load_env_files()` to search `<exe_dir>/.env`, root `.env`, `%APPDATA%\Cineforge\.env`, `backend/.env`, and `frontend/.env`.
  - *Fix 3 (Compact Hero Fallback Notice)*: Designed `.hero-fallback-shell` and `.home-hero-fallback` in `index.css`: a compact (~140px), non-intrusive notification card with friendly user copy ("Trending Highlights Offline", "Check your connection or search for titles directly below") and an inline Retry action, preventing huge layout voids without hiding errors or inventing fake movies.
- **UI/UX Polish: Telegram QR Dialog & Native Alert Replacement**:
  - *QR Card Layout & Contrast*: Refactored `TelegramConnectModal.jsx` to center the QR code on a crisp, rounded white card with strict aspect-ratio containment and dark modules (`#0c0e14`). Eliminated SVG container overflow that previously overlapped instructions.
  - *Design System Harmony*: Matched Cineforge's dark theme palette (`--ink`, `--panel-2`, `--edge`, `--ember`), with numbered step badges and animated pulsing connection indicators. Fully responsive to window resizing.
  - *Replaced Native Alerts*: Replaced all blocking browser-native `window.confirm()` and `window.alert()` calls with a non-blocking `ConfirmModal` (accessible ARIA dialog with autofocus and Escape/Enter keyboard navigation) and auto-dismissing `Toast` notifications, orchestrated through a clean React `DialogContext`.
- **Cargo Multi-Binary Default Runner Fix**:
  - *Root Cause*: When `cineforge-provisioner` was added alongside `cineforge` as a second binary in `src-tauri/Cargo.toml`, Cargo could not infer which binary `cargo run` should execute during `npm run tauri:dev`, failing with `could not determine which binary to run`.
  - *Fix*: Configured `default-run = "cineforge"` in `src-tauri/Cargo.toml` under `[package]` and passed explicit runner arguments (`npx @tauri-apps/cli dev -- --bin cineforge`) in root `package.json`. Keeps the remote provisioning service as a dedicated standalone binary while guaranteeing zero-friction startup for desktop development.

---

### Stage 4.2: Telegram Media Search & Result Selection
- **Bot Interaction Architecture**:
  - Implemented `TelegramSearchService` communicating over pure MTProto with the configured Telegram bot (`@Spoty_xbot` by default or `TELEGRAM_BOT_USERNAME`).
  - Reuses the authorized user's personal session from Stage 4.1 (`get_client()`). If not logged in, returns `401 Unauthorized` with a clear user prompt to connect their Telegram account.
- **Robust Parser (`telegram_search_parser.rs`)**:
  - Parses complex Telegram bot messages and inline keyboard matrices (`KeyboardInlineButtonRow` / `KeyboardInlineButton`).
  - Cleans messy release strings, extracts resolution tags (`2160p`, `1080p`, `720p`, `480p`), containers (`.mp4`, `.mkv`), exact byte sizes (`parse_size_bytes`), and language classification (`categorize_language`).
  - Language detection uses word-boundary regexes to prevent partial substring matches (e.g., distinguishing "Interstellar" from "Telugu").
  - Identifies browser playability (marking MP4/H.264/AAC as natively playable in webview, while MKV/HEVC requires transcoder or external player handoff).
  - Normalizes inline buttons into `SearchCandidate` models with deterministic `candidate_id` hashes.
- **Access Control & FSub (Force Subscribe) Gate Detection**:
  - Detects Telegram bot channel membership requirements ("must join our channel", "join updates channel to continue").
  - Extracts the required channel handle/invite link and returns a structured `ChannelRequirement` response without attempting to circumvent channel gates.
- **Pagination & Progressive Aggregation**:
  - Detects pagination indicators (`Total Results: X`, `Page: X/Y`, `[1/5]`, `[Next >>]`) from bot text and navigation buttons.
  - Automatically aggregates multi-page results up to `max_pages` when requested.
- **Search Endpoints & API Contract**:
  - Added `/api/search`, `/api/search/suggestions`, `/api/search/select`, and `/api/search/versions` to the local Axum router.
  - Handles timeouts (504), Telegram rate limits (429 with retry seconds), and empty search results with descriptive error payloads.
  - Desktop frontend integration via `selectCandidate` in `frontend/src/services/api.js` and `frontend/src/App.jsx`, preparing candidate metadata for Stage 4.3 streamer handoff.
- **Grammers TL Types 0.12 Compatibility**:
  - Handled Grammers TL layer updates: `ResolveUsername` with `referer: None`, `ResolvedPeer::Peer`, `SendMessage` with modern TL flags (`allow_paid_floodskip`, `allow_paid_stars`), and nested inline markup rows (`ReplyInlineMarkup` -> `KeyboardInlineButtonRow` -> `KeyboardInlineButton` -> `InlineButtonType`).
- **Comprehensive Test Coverage**:
  - 34 Rust unit and integration tests passing (`cargo test`).
  - Node API routing integration tests verified with desktop mock server (`node frontend/test_api_routing.mjs`).
  - Frontend production build verified (`npm run build`).

### Stage 4.3: Go Streamer Sidecar Packaging & Local Progressive Video Streaming
- **Go Streamer Sidecar Packaging**:
  - Reused the existing precompiled `TG-FileStreamBot/fsb.exe` (v3.2.0, compiled Go binary) without requiring Go compiler installation.
  - Placed at `src-tauri/binaries/fsb-x86_64-pc-windows-msvc.exe` following Tauri 2 sidecar conventions.
  - Declared in `src-tauri/tauri.conf.json` under `bundle.externalBin: ["binaries/fsb"]`.
- **Sidecar Lifecycle Manager (`StreamerSidecarService`)**:
  - Automatically discovers executable location (dev paths, Tauri resource directory, or project root).
  - Configures child process working directory to `TG-FileStreamBot` (or `%APPDATA%\Cineforge`) to load `fsb.env` and `fsb.session`.
  - Binds to an ephemeral loopback port (`127.0.0.1:0`) to eliminate port conflicts.
  - Spawns `fsb run --port <port> --host http://127.0.0.1:<port>` with `kill_on_drop(true)`.
  - Polls `http://127.0.0.1:<port>/` health check until responsive before accepting traffic.
  - Background watchdog task tracks process lifecycle and updates `StreamerStatus::Running` or `StreamerStatus::Exited`.
  - Clean graceful shutdown hooked into Axum and Tauri shutdown signals.
- **Telegram Delivery Coordinator (`TelegramDeliveryService`)**:
  - Verifies the user's personal Telegram session is active before making requests (`401 Unauthorized` if disconnected).
  - Triggers candidate release via callback button (`messages.getBotCallbackAnswer`) or deep-link `/start <payload>`.
  - Waits for document message from search bot, handling FSub channel requirements (`403 Forbidden` with structured `ChannelRequirement`).
  - Forwards document to Saved Messages (`me`) and the Go streamer bot (`@stre89d_bot`) using Grammers TL `ForwardMessages`.
  - Polls streamer bot for generated streaming link (`/stream/<id>?hash=<hash>`).
  - Constructs local proxy URL `http://127.0.0.1:<axum_port>/api/stream/<id>?hash=<hash>`.
- **Progressive Byte-Range Stream Proxy (`api/stream.rs`)**:
  - Routes `GET` and `HEAD` on `/stream/{message_id}` and `/api/stream/{message_id}`.
  - Forwards incoming `Range` header (e.g. `bytes=0-1023` or `bytes=1048576-`) to upstream Go streamer.
  - Streams chunked bytes asynchronously (`Body::from_stream`) with zero in-memory buffering.
  - Forwards `Content-Range`, `Content-Length`, `Content-Type`, and sets `Accept-Ranges: bytes` with CORS headers.
  - Emits `206 Partial Content` on byte-range queries, enabling instantaneous video scrubbing and timeline seeking.
- **Player Compatibility & Format Detection**:
  - Inspects MIME types and container extensions.
  - MP4 container with H.264 video and AAC audio is classified as `browser_playable: true` (`playback_mode: "browser"`), playing directly in Chromium/WebView2.
  - MKV container or HEVC/AC3 codecs are classified as `browser_playable: false` (`playback_mode: "external"`), ready for handoff to the Stage 5 native player.
- **Frontend Delivery Routing (`api.js`)**:
  - `deliverCandidate` in desktop mode calls `/api/search/deliver`.
  - Propagates descriptive errors and FSub requirements without silently falling back to mock Google Cloud Storage URLs.
- **Testing & Verification**:
  - 45 Rust tests passing (`cargo test`).
  - Node API routing test suite verified end-to-end (`npm --prefix frontend test`).
  - Vite production build verified (`npm --prefix frontend run build`).

---

### Stage 4.4: Channel-Free Go Streamer Architecture (`TG-FileStreamBot`)
- **Goal**:
  - Remove the requirement for a public or private Telegram `LOG_CHANNEL` in local desktop mode.
  - Enable each user's personal streamer bot to stream files directly from its private chat with the user without needing to create or manage channels, or forward files to shared bots like `@stre89d_bot`.
- **Config & Loopback Binding**:
  - Made `LOG_CHANNEL` optional in `config.go` (defaults to `0` instead of failing startup).
  - In `run.go`, bound the Gin HTTP router strictly to `127.0.0.1:%d` instead of public interfaces `:%d`.
  - In `internal/bot/userbot.go`, added guards to skip channel verification if `LogChannelID == 0`.
  - Updated `StreamerSidecarService` in Rust to launch `fsb.exe` with `LOG_CHANNEL=0`.
- **Direct Private-Chat Stream & In-Memory Priming**:
  - In `internal/commands/stream.go` (`sendLink`):
    - When `LogChannelID == 0`, extracts `file` directly from the incoming message media without forwarding to any channel.
    - Uses incoming `messageID = u.EffectiveMessage.ID`.
    - Primes the fast in-memory cache immediately: `key := fmt.Sprintf("file:%d:%d", messageID, ctx.Self.ID)`.
    - Generates stream URLs (`/stream/{message_id}?hash={hash}`) using the incoming message ID.
- **Cache Serialization & Cache Miss Resilience**:
  - In `internal/cache/cache.go`: registered `&tg.InputDocumentFileLocation{}` and `&tg.InputPhotoFileLocation{}` with `encoding/gob` for pointer serialization into the `tg.InputFileLocationClass` interface.
  - In `internal/utils/helpers.go` (`GetTGMessage`):
    - On cache miss, issues MTProto `messages.getMessages` to retrieve the message directly from the bot's private chat.
    - Validates that the message belongs to a private dialogue (`PeerUser`) and matches `AllowedUsers` if configured.
    - Rejects invalid IDs and non-private messages.
    - Increased cache TTL to 86,400 seconds (24 hours) for persistent scrubbing and seeking.
- **Byte-Range Seeking & Progressive Streaming**:
  - Retained chunked byte-range requests (`calculateBlockSize`), MTProto `upload.getFile` streaming, and `206 Partial Content` delivery without loading complete videos into RAM.
- **Sidecar Rebuild & Test Verification**:
  - AGPL-3.0 source license preserved intact.
  - Added unit test suites: `config_test.go` (optional log channel), `stream_range_test.go` (block size calculation), and `channel_free_stream_test.go` (cache priming, hash checking, cache miss lookup).
  - Rebuilt `src-tauri/binaries/fsb-x86_64-pc-windows-msvc.exe` from source (49.5 MB).
  - All Go unit tests, Rust tests (45 passed), and frontend test suites passing cleanly.

### Stage 4.5: Personal Streamer Bot Provisioning & Remote HTTPS Architecture
- **Goal**:
  - Automatically create and reuse exactly one personal streamer bot per connected Telegram account.
  - Keep manager-bot credentials strictly inside a remote HTTPS provisioning service (zero manager tokens bundled in client, Go binary, or Git).
  - Verify account ownership via Telegram cryptographic challenge without trusting client-supplied IDs.
  - Maintain primary account-to-bot mapping in the remote service, backed by local Windows DPAPI encrypted cache (`telegram_bot.enc`).
  - Pass the personal bot token to `TG-FileStreamBot` only at runtime with `LOG_CHANNEL=0`, stopping the sidecar and clearing runtime tokens on logout.
  - Route media forwarding from `@Spoty_xbot` directly to the user's personal bot, eliminating `@stre89d_bot`.
- **Implementation Highlights**:
  - **Durable Storage**: Added `save_encrypted_bot_mapping` / `load_encrypted_bot_mapping` in `storage.rs` using Windows DPAPI.
  - **Models**: Created `models/provisioning.rs` with `PersonalBotMapping`, `PersonalBotInfo`, `ChallengeRequest`, `ChallengeResponse`, `RegisterBotRequest`, `TokenRequest`, and `TokenResponse`.
  - **Standalone Provisioner Binary**: Created `src/bin/provisioner.rs` (`cineforge-provisioner`) with Axum, handling challenge creation, Telegram `/verify` message ingestion, durable JSON store (`managed_bots.json`), and MTProto `bots.exportBotToken`.
  - **Desktop Provisioning Service**: Created `services/bot_provisioning.rs` managing the challenge lifecycle, bot creation (`bots.createBot`), username checking (`bots.checkUsername`), and in-memory runtime token cache.
  - **Sidecar Lifecycle**: Updated `StreamerSidecarService` with `start_with_token` and clean shutdown in `stop()` purging temporary SQLite files (`fsb.session`).
  - **Delivery Integration**: Updated `TelegramDeliveryService` to ensure the personal bot is provisioned and forward candidate media directly to the personal bot username.
  - **UI Disclosure & Badge**: Added consent copy and active bot status card to `TelegramConnectModal.jsx`.
- **Verification**:
  - 47 Rust tests passing (`cargo test`).
  - Frontend production build verified (`npm run build`).
  - API routing tests passing (`npm test`).

---

## Architectural Decisions & Concepts Learned

1. **Windows Data Protection API (DPAPI)**:
   - *Concept*: Operating-system-level encryption where symmetric keys are derived from the current logged-in Windows user's logon credentials.
   - *Implementation*: Linked via Windows C FFI (`crypt32::CryptProtectData` and `crypt32::CryptUnprotectData`).
   - *Why it matters*: Guarantees that even if an attacker or unauthorized process copies the `.enc` file, it cannot be decrypted outside the user's authenticated Windows session.

2. **MTProto Login State Machine**:
   - Authentication transitions through explicit states: `Disconnected` -> `QrPending` / `CodePending` -> `PasswordPending` (for 2FA) -> `Connected`.
   - Polling `auth.exportLoginToken` detects when the mobile Telegram app approves the login token and yields `auth.LoginTokenSuccess`.

3. **Telegram Bot Inline Keyboards vs Text Response Parsing**:
   - *Challenge*: Media delivery bots in Telegram rarely return standard JSON APIs; they return human-formatted messages containing formatted inline keyboards (`inline_keyboard`) with callback buttons (`data`), deep-link URLs (`t.me/...`), and pagination rows.
   - *Solution*: Developed a dedicated AST parser (`telegram_search_parser.rs`) that evaluates button types, splits navigation buttons (`Next`, `Prev`, `Back`) from candidate releases, computes quality tiers, and derives stable candidate IDs.

4. **Force-Subscription (FSub) Gate Compliance**:
   - *Ethical & Protocol Requirement*: Many public search bots require users to be members of an updates channel before fulfilling file delivery callbacks.
   - *Implementation*: Rather than attempting to bypass or hack access gates, Cineforge detects the gate, parses the channel link, and presents an actionable "Join Channel" dialog in the UI.

5. **Tauri 2 External Binary (Sidecar) Lifecycle & Ephemeral Port Orchestration**:
   - *Concept*: Instead of reimplementing a battle-tested high-concurrency Go streamer, Tauri allows bundling native sidecars.
   - *Implementation*: Rust spawns the child process with a dynamically chosen ephemeral port (`127.0.0.1:0`), monitors its health over HTTP, proxies traffic with byte-range headers, and kills the process on shutdown (`kill_on_drop`).

6. **Progressive Byte-Range HTTP Streaming (`206 Partial Content`)**:
   - *Concept*: Video players do not download entire gigabyte files before playback; they request 512KB-2MB byte ranges (`Range: bytes=start-end`) as the playback head advances.
   - *Implementation*: Axum streams chunked bytes asynchronously (`bytes_stream() -> Body::from_stream`) without loading the video into system RAM, propagating `Content-Range: bytes start-end/total`.

7. **Browser Video Compatibility (MP4 vs MKV/HEVC)**:
   - *Limitation*: Chromium/WebView2 natively decodes MP4 containers (H.264/AAC), but lacks native decoders for MKV containers and proprietary codecs (HEVC/AC3/DTS).
   - *Design*: Candidates are tagged with `browser_playable: true/false`. Browser-playable streams play directly in the existing React `<video>` player; non-playable formats will be handed off to a dedicated player (VLC / MPV / libvlc) in Stage 5.

8. **Channel-Free Streaming with In-Memory Caching & Gob Serialization**:
   - *Problem*: Traditional Telegram stream bots forward media to a Telegram channel (`LOG_CHANNEL`) to establish a permanent channel message ID and file reference. Creating private channels for every desktop user requires channel creation quotas, creates clutter in the user's Telegram chat list, and introduces failure modes.
   - *Solution*: In MTProto v2, `upload.getFile` operates purely on `InputDocumentFileLocation` (`id`, `access_hash`, `file_reference`) without requiring a channel peer. The bot now extracts metadata directly from incoming private messages, primes the in-memory cache under `file:{message_id}:{bot_id}`, and serves byte-range streaming requests immediately. On cache misses, it queries the bot's private chat mailbox using MTProto `messages.getMessages`.

9. **Cryptographic Telegram Account Ownership Challenge-Response**:
   - *Problem*: If a desktop client merely submits a Telegram `user_id` to a provisioning backend, any rogue client could impersonate someone else's account to steal their personal streamer bot token.
   - *Solution*: The Provisioning Service generates a single-use, 60-second `challenge_nonce`. The user's MTProto client sends `/verify <nonce>` to `@CineforgeManagerBot` directly through Telegram's encrypted MTProto transport. Telegram's servers authenticate and append the sender's real Telegram `user_id` to the message. The Provisioning Service verifies this sender ID before exporting the bot token, rendering account spoofing mathematically impossible without controlling the user's Telegram session.

10. **Security Hardening & Single-Use State Machine for Remote Provisioning**:
    - *CSPRNG Nonce Generation*: Replaced pseudo-random timestamp nonces with 256 bits of cryptographic entropy sampled from OS CSPRNG (`ring::rand::SystemRandom`). Nonces are 64 lowercase hex characters with zero collision risk.
    - *Telegram Verification Before Trust*: `/api/provision/register` no longer trusts client-supplied parameters. Before recording mappings or exporting tokens, the manager bot verifies via MTProto (`bots.exportBotToken` + `users.getUsers` + `UpdateManagedBot` event tracker) that the bot was created with this manager bot as its manager, is owned by the verified Telegram user, and has the matching bot username.
    - *Explicit State Machine*: Modeled challenge lifecycle as `PendingVerification -> Verified -> Registered { bot_id } -> Consumed`. Replays and duplicate registration attempts are rejected. Existing account-to-bot mappings cannot be overwritten by another challenge.
    - *Atomic Persistence*: Replaced async file writes with atomic temp-file write, `flush()`, `sync_all()`, and atomic replace (`std::fs::rename`). Surface write errors to callers instead of swallowing them.
    - *Fail-Closed Startup*: Production provisioner refuses to start if `CINEFORGE_MANAGER_BOT_TOKEN`, `CINEFORGE_MANAGER_BOT_USERNAME`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, or `DATA_DIR` are missing or mock. Removed fake token fallbacks in production.
    - *Client HTTPS Enforcement*: Desktop client enforces `https://` for remote provisioning URLs, permitting plain `http://` only for explicit loopback addresses (127.0.0.1, localhost) or explicit dev mode.
    - *Abuse Prevention & Sanitization*: Axum 64KB `DefaultBodyLimit`, sliding-window `RateLimiter` (20 req/min per key), and sanitized log output (tokens redacted, nonces truncated to first 6 chars).

11. **Render Deployment Readiness & Persistent Storage Architecture**:
    - *Containerization*: Created multi-stage [`Dockerfile.provisioner`](file:///C:/Users/manuk/Downloads/projects/Cineforge/Dockerfile.provisioner) packaging `cineforge-provisioner` into a lightweight, secure `debian:bookworm-slim` runner with CA certificates and zero desktop GUI baggage.
    - *Declarative Blueprint*: Updated [`render.yaml`](file:///C:/Users/manuk/Downloads/projects/Cineforge/render.yaml) defining `cineforge-provisioner`, health checks at `/health`, and unsynced private secrets (`sync: false`).
    - *Health & Diagnostics*: Added `GET /` online status endpoint and verified `GET /health` responding with layer 233 MTProto status.

12. **Supabase Bot Store for Render Free Tier Resilience**:
    - *Problem*: Free-tier containers on Render spin down after 15 minutes of inactivity and execute on an ephemeral filesystem, wiping local files (`managed_bots.json`) on restart. Persistent disks require a paid plan (\$7/mo Starter).
    - *Architecture*: Offloaded account-to-bot durable mappings to Supabase Postgres (`public.managed_bots`) via PostgREST HTTP queries using `reqwest`. Render remains purely stateless, enabling deployment on Render's 100% Free plan.
    - *Zero Tokens in Database*: Only non-sensitive metadata (`telegram_user_id`, `bot_id`, `bot_access_hash`, `bot_username`, timestamps) is stored in Supabase. Personal bot tokens are exported strictly on-the-fly via MTProto and delivered directly to the client's volatile RAM over HTTPS.
    - *Strict RLS Lockdown & Immutability Enforcement*: Table has Row Level Security enabled. All permissions are revoked from `PUBLIC`, `anon`, and `authenticated`. Only the backend `service_role` has `SELECT, INSERT` access. Database trigger `trg_prevent_managed_bot_update` and primary key/unique constraints strictly reject any `UPDATE` or duplicate overwrite attempts, returning an explicit `409 Conflict`.
    - *HTTPS Enforcement*: Production startup requires `SUPABASE_URL` to begin with `https://`. Plain HTTP is rejected and allowed only for local loopback addresses (`localhost` / `127.0.0.1`) in explicit dev mode.
    - *Fail-Closed Health & Error Handling*: If Supabase is unreachable or returns an error during challenge or token requests, the provisioner returns a clear `503 Service Unavailable` error instead of silently creating duplicate bots or inventing fake tokens.

13. **Force-Subscription (FSub) Gate Resolution & Explicit User Consent Safeguards**:
    - *Strict Domain Filtering*: Added `parse_channel_link()` rejecting non-Telegram URLs to protect against phishing or off-platform malicious links. Distinguishes public handles (`@channel`, `t.me/channel`) from private invite hashes (`t.me/+hash`, `t.me/joinchat/hash`).
    - *Zero Silent Joins*: Cineforge never silently joins channels on behalf of the user. Membership requirements halt delivery and surface an accessible confirmation dialog showing the channel handle/URL and requesting explicit approval.
    - *Telegram Datacenter Sync Delay*: MTProto `JoinChannel` / `ImportChatInvite` is followed by a 2.5-second propagation delay to ensure Telegram datacenter caches (`getChatMember`) update before activating bot retry actions.
    - *Bounded Retries*: Bot retry callbacks (`GetBotCallbackAnswer`) and start commands (`/start <payload>`) are capped at 2 iterations to prevent infinite retry loops.
    - *Telegram RPC Edge Cases*: Gracefully handles `USER_ALREADY_PARTICIPANT` as immediate success, `INVITE_REQUEST_SENT` with informative feedback regarding pending admin approval, and `FLOOD_WAIT` with exact seconds.

---

## Next Steps
- **Stage 4.7 (Owner Setup & Live End-to-End Verification)**:
  - Run migration `supabase/migrations/20261122_managed_bots.sql` in Supabase SQL Editor.
  - Owner enables Bot Management in `@BotFather` for `@CineforgeManagerBot`.
  - Deploy `cineforge-provisioner` to Render Free tier with the 8 environment variables.
  - Live end-to-end testing with an authorized Telegram test account (personal bot creation, remote token delivery, local sidecar startup, video playback, and logout cleanup).
- **Stage 5**: Native desktop video player integration (MPV / LibVLC / custom Tauri player window) to support MKV, 4K HEVC, and multi-track audio without transcoding.
