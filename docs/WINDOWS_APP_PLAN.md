# Cineforge Windows App Plan

## Agreed direction

- Build a public Windows desktop app; the user installs it and runs Cineforge locally.
- Do not require a cloud-hosted Cineforge product backend for search, Telegram access, or playback. Internet access is still required for Telegram and online metadata/services.
- Use Tauri for the desktop shell, retain the React UI where practical, and migrate backend responsibilities from Python to Rust over time.
- Use VLC/libVLC as the native playback engine so supported MKV/container and codec combinations play directly without Cineforge transcoding.
- Each user connects their own Telegram account. Never bundle a user's Telegram session or credentials. Store each user's session securely on their own device.
- Keep Telegram onboarding simple: users should not need to register their own Telegram `api_id`/`api_hash`. Use Cineforge's registered app credentials to identify the client, then have each user connect their own Telegram account. The app credentials do not identify the logged-in account; the per-user Telegram authorization session does.
- Every Telegram action in the desktop flow must use that user's local session: search `@Spoty_xbot`, receive the selected file, forward it to that user's Saved Messages, and hand it to the streamer bot. Do not let the Go streamer or any helper silently fall back to the developer's shared Telegram session.
- The current Python backend uses a single configured Telegram session. Replacing that singleton with per-user local sessions is a required migration task before public streaming; merely adding a Telegram login screen is not enough.
- Existing Go `TG-FileStreamBot` may remain as a bundled, automatically managed local helper if the migration still needs it.
- Publish releases through a signed update flow. The app can check for releases and show notes/update prompts; no Cineforge user identity is needed for this.
- Later, add a separate cloud admin/analytics service. The desktop app can send limited product-health and usage events to an admin dashboard while core Cineforge services stay local.
- Analytics should be clearly disclosed and preferably opt-in. Do not send Telegram credentials/session data, search text, movie titles, filenames, stream URLs, or other viewing details. Use a random install ID and aggregate version, launch, crash, and playback-error events.

## Suggested phases (deferred)

1. Audit current features and dependencies; define the desktop/web boundary.
2. Add the Tauri shell around the existing React frontend without breaking the web app.
3. Build Rust local services and first-run setup, including a per-user Telegram login stored securely on that user's PC.
4. Port Telegram search, candidate selection, delivery, Saved Messages handoff, and streamer-bot handoff to use the same per-user session end to end.
5. Integrate libVLC and verify local files and direct remote streams, seeking, audio tracks, and subtitles.
6. Port the remaining backend features incrementally; keep Python as a fallback until parity is demonstrated.
7. Bundle required local helpers and create a Windows installer that users can run without separately installing Python, Node, Rust, VLC, or Go.
8. Add signed release checks and in-app update notices.
9. Later, implement the optional cloud analytics/admin dashboard with privacy controls, limited event collection, and retention rules.

## Important boundaries and open decisions

- “One installer” means one downloadable setup `.exe`; the installed program may include supporting runtime files.
- Telegram, TMDb, Gemini, and similar online services still require internet. Local playback can work offline for files already on the device.
- Decide later whether analytics is opt-in by default, which exact metrics are useful, and how long event data is retained.
- Decide later whether to retain Supabase for optional account sync, or keep desktop settings/history local only.
- The app-level Telegram credentials are shared Cineforge client credentials; Telegram account authorization is unique per user. Verify Telegram's current requirements and distribution guidance before public release.
- Verify Telegram API requirements and licenses for VLC and bundled components before public distribution.
- The Tauri shell and local Axum health-service foundation have been scaffolded. Per-user Telegram migration, streaming, VLC, Supabase admin features, and analytics are still later work; this file records the agreed direction and sequence.

---

## Remote Personal Bot Provisioning Architecture & Setup Guide

### 1. Architectural Boundaries & Principles
- **No Shared Manager Token in Client**: The client application (Tauri / Rust) and bundled Go binaries NEVER contain the manager bot token or master Telegram credentials.
- **Remote HTTPS Hosting**: The provisioning service runs as an independent backend (`cineforge-provisioner`) reachable strictly over HTTPS in production.
- **Zero Video Data in Provisioner**: The provisioner handles cryptographic challenge authentication, bot creation validation, and token export only. No video or streaming data ever passes through it.
- **Loopback-Only Local Streaming**: The bundled `TG-FileStreamBot` runs exclusively on loopback (`127.0.0.1:<ephemeral_port>`) and serves video byte-range requests directly to the desktop app.

### 2. Hosting Requirements
- **Runtime Environment**: Docker container, Linux VPS, or container service (e.g., Fly.io, Railway, Cloud Run, AWS ECS).
- **Public Networking**: Valid domain with HTTPS / TLS termination (Let's Encrypt, Cloudflare, or reverse proxy like Caddy / Nginx).
- **Storage Volume**: Persistent directory mounted at `/data` (configured via `DATA_DIR`) for durable storage of `managed_bots.json`.
- **Resources**: Lightweight (single binary ~15MB, <64MB RAM, <0.2 vCPU).

### 3. Server Secrets & Environment Variables
The remote provisioning service fails closed on startup if any required secret is missing in production mode:
- `CINEFORGE_MANAGER_BOT_TOKEN`: The Telegram Bot API token obtained from @BotFather for the Manager Bot.
- `CINEFORGE_MANAGER_BOT_USERNAME`: The Telegram username of the Manager Bot (e.g. `CineforgeManagerBot`).
- `TELEGRAM_API_ID`: The Telegram application API ID (integer) used for MTProto communication.
- `TELEGRAM_API_HASH`: The Telegram application API hash used for MTProto authentication.
- `DATA_DIR`: Directory where `managed_bots.json` is stored (defaults to `./data`). Must have read/write permissions.
- `PORT`: HTTP port to bind (default `8085`).
- `CINEFORGE_DEV_MODE`: Set to `true` only for offline developer testing. When unset or `false`, production fail-closed security rules apply.

### 4. How the Owner Enables Bot Management Mode in @BotFather
To allow the Manager Bot to manage user-created streamer bots and export their tokens via MTProto:
1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2. Send `/mybots` and select your Manager Bot (e.g., `@CineforgeManagerBot`).
3. Click **Bot Settings**.
4. Click **Bot Management** (or **Allow Managed Bots** / **Management Mode**).
5. Toggle it to **Enabled** / **Turn On**.
6. When enabled, users can create bots specifying this Manager Bot as their `manager_id`, and the Manager Bot is authorized to invoke `bots.exportBotToken`.

### 5. User-Bot Mapping Lifecycle
1. **First Connection**:
   - User signs into Telegram via the desktop client (QR or phone).
   - App checks local DPAPI cache (`telegram_bot.enc`) and requests challenge from remote provisioning service.
   - Remote service generates 256-bit CSPRNG single-use nonce (TTL 60s).
   - User's MTProto session sends `/verify <nonce>` to the Manager Bot.
   - Manager bot verifies sender ID == user ID and marks challenge as `Verified`.
   - User MTProto invokes `bots.createBot` passing Manager Bot as `manager_id`.
   - App calls `/api/provision/register`. Remote service verifies via MTProto that the bot is managed by this Manager Bot and belongs to the verified user. Atomic save to `managed_bots.json`.
   - App calls `/api/provision/token`. Challenge is burned (`Consumed`). Token is returned and kept strictly in volatile RAM.
   - Account-to-bot mapping is cached locally in Windows DPAPI storage (`telegram_bot.enc`).
2. **App Restarts / Re-opens**:
   - On launch, if user is already logged in, app loads bot info from DPAPI cache.
   - To obtain runtime token, app issues a fresh single-use challenge to the remote service.
   - Remote service recognizes existing durable mapping in `managed_bots.json`, verifies challenge, burns it, and exports the token. No new bot is ever created.
3. **Logout**:
   - User disconnects Telegram.
   - Local Go streamer sidecar (`fsb.exe`) is stopped immediately.
   - In-memory runtime tokens and temporary database files (`fsb.session`) are wiped from RAM and disk.
   - The remote mapping in `managed_bots.json` remains permanently so reconnecting reuses the exact same bot.
4. **Different PC / Re-login**:
   - When user logs in on a new PC, remote provisioner looks up their Telegram ID in `managed_bots.json`. The user reuses their existing personal streamer bot seamlessly.

### 6. Verification Status & Next Steps
- **Unit & Mock Verification**: All 55 Rust tests (including CSPRNG nonce uniqueness, challenge state machine, ownership verification, atomic persistence, rate limiting, and HTTPS URL enforcement) and frontend test suites pass offline.
- **Subsequent Live Step**: Live end-to-end verification against real Telegram servers with a live Manager Bot and test account is a subsequent step that requires owner deployment and credentials.

---

## Render & Supabase Free-Tier Deployment Guide: Personal-Bot Provisioning Service

### 1. Hybrid Free-Tier Architecture (Stateless Render + Durable Supabase)
To enable testing on **100% free services** without losing saved user-bot connections when containers sleep or restart:
- **Render Free Web Service (`cineforge-provisioner`)**: Handles bot creation verification, single-use cryptographic challenges, and on-the-fly token export via MTProto. Operates completely statelessly (no local disks or SQLite files required).
- **Supabase Postgres Database (`public.managed_bots`)**: Durably persists only the account-to-bot mapping (`telegram_user_id`, `bot_id`, `bot_access_hash`, `bot_username`, and timestamps).
- **CRITICAL SECURITY RULE**: Personal streamer bot tokens are **NEVER** stored in Supabase or written to disk. Tokens are exported on-the-fly via Telegram MTProto and delivered directly into the desktop client's volatile RAM over HTTPS.
- **Zero Video Data**: Neither Render nor Supabase ever receives, proxies, or stores video stream data.

### 2. Step 1: Apply Supabase Database Migration

Before deploying on Render, create the secured `managed_bots` table in your Supabase project:

1. Open your [Supabase Dashboard](https://supabase.com/dashboard) and select your Cineforge project.
2. In the left navigation sidebar, click the **SQL Editor** icon (`>_`).
3. Click **+ New Query**.
4. Open [`supabase/migrations/20261122_managed_bots.sql`](file:///C:/Users/manuk/Downloads/projects/Cineforge/supabase/migrations/20261122_managed_bots.sql) in this repository, copy its full contents, and paste them into the SQL Editor:
   ```sql
   CREATE TABLE IF NOT EXISTS public.managed_bots (
       telegram_user_id BIGINT PRIMARY KEY,
       bot_id BIGINT NOT NULL,
       bot_access_hash BIGINT NOT NULL,
       bot_username TEXT NOT NULL,
       created_at BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
       updated_at BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
       CONSTRAINT uq_managed_bots_bot_id UNIQUE (bot_id)
   );

   COMMENT ON TABLE public.managed_bots IS 'Durable account-to-bot mappings for Cineforge. Bot tokens are never stored in the database. Existing rows are immutable.';

   ALTER TABLE public.managed_bots ENABLE ROW LEVEL SECURITY;

   -- 1. Explicitly revoke ALL table privileges from all roles, including service_role
   REVOKE ALL ON TABLE public.managed_bots FROM PUBLIC, anon, authenticated, service_role;

   -- 2. Grant strictly SELECT and INSERT to service_role (prevent UPDATE / DELETE)
   GRANT SELECT, INSERT ON TABLE public.managed_bots TO service_role;

   -- 3. Row Level Security policies for service_role strictly for SELECT and INSERT
   DROP POLICY IF EXISTS "Allow service_role full access to managed_bots" ON public.managed_bots;
   DROP POLICY IF EXISTS "Allow service_role select on managed_bots" ON public.managed_bots;
   DROP POLICY IF EXISTS "Allow service_role insert on managed_bots" ON public.managed_bots;

   CREATE POLICY "Allow service_role select on managed_bots"
       ON public.managed_bots
       FOR SELECT
       TO service_role
       USING (true);

   CREATE POLICY "Allow service_role insert on managed_bots"
       ON public.managed_bots
       FOR INSERT
       TO service_role
       WITH CHECK (true);

   -- 4. Enforce immutability at the database level:
   CREATE OR REPLACE FUNCTION public.prevent_managed_bot_replacement()
   RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'Account mapping conflict: updating or replacing an existing managed bot mapping for Telegram user % is strictly prohibited.', OLD.telegram_user_id
           USING ERRCODE = 'check_violation';
   END;
   $$ LANGUAGE plpgsql;

   DROP TRIGGER IF EXISTS trg_prevent_managed_bot_update ON public.managed_bots;
   CREATE TRIGGER trg_prevent_managed_bot_update
       BEFORE UPDATE ON public.managed_bots
       FOR EACH ROW
       EXECUTE FUNCTION public.prevent_managed_bot_replacement();
   ```
5. Click **Run** (or press `Ctrl+Enter`).
6. Confirm that the query succeeds with `Success. No rows returned`.
7. **Security Verification**: Row Level Security (RLS) is strictly enabled. All read, write, and execute permissions are revoked from `anon` and `authenticated` roles. Public visitors and the desktop frontend are strictly blocked by PostgreSQL from accessing bot records. Only the hosted helper on Render using the secret `service_role` key can read and write mappings.

### 3. Step 2: Retrieve Supabase Server Credentials

In your Supabase project dashboard:
1. Go to **Project Settings** (gear icon at the bottom of the sidebar) → **API**.
2. Locate the following two values under **Project API keys** and **Config**:
   - **Project URL**: e.g. `https://your-project-id.supabase.co`
   - **service_role secret key**: (Click *Reveal* next to `service_role`). Copy this key.
   > [!CAUTION]
   > **Never share or expose the `service_role` key.** Do not place it in frontend files, Git repositories, or the desktop installer. It belongs exclusively in Render's private environment variables.

### 4. Step 3: Deploy `cineforge-provisioner` on Render

Render automatically provides an official TLS/HTTPS certificate for every deployed service using its `*.onrender.com` subdomain (e.g. `https://cineforge-provisioner.onrender.com`). You do **not** need a custom domain.

#### Option A: Blueprint Deployment (Recommended)
1. In the [Render Dashboard](https://dashboard.render.com), click **New +** → **Blueprint**.
2. Connect your GitHub repository (`Cineforge`).
3. Render reads [`render.yaml`](file:///C:/Users/manuk/Downloads/projects/Cineforge/render.yaml) automatically, selects the **Free** instance plan, and presents the un-synced private secrets.
4. Enter your real values (kept privately by Render) and click **Apply**:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `CINEFORGE_MANAGER_BOT_TOKEN`
   - `CINEFORGE_MANAGER_BOT_USERNAME`
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`

#### Option B: Manual Web Service Creation
1. In the Render Dashboard, click **New +** → **Web Service**.
2. Select **Build and deploy from a Git repository** and pick `Cineforge`.
3. Configure the **Service Details**:
   - **Name**: `cineforge-provisioner`
   - **Region**: Choose closest to you (e.g. `Oregon (US West)` or `Frankfurt (EU Central)`).
   - **Branch**: `main`
   - **Root Directory**: Leave blank (repo root).
   - **Runtime**: Select **Docker**.
   - **Dockerfile Path**: `./Dockerfile.provisioner`
   - **Instance Type**: Select **Free** (\$0/month).
   - *(No disk required — leave Disks empty!)*
4. Configure **Health Check**:
   - **Health Check Path**: `/health`
5. Add **Environment Variables** (under Environment tab):
   | Key | Value / Placeholder | Notes |
   | :--- | :--- | :--- |
   | `PORT` | `10000` | Render default web port |
   | `CINEFORGE_DEV_MODE` | `false` | Enforces production fail-closed security |
   | `SUPABASE_URL` | `https://<YOUR_PROJECT_ID>.supabase.co` | From Supabase Project Settings → API |
   | `SUPABASE_SERVICE_ROLE_KEY` | `<YOUR_SUPABASE_SERVICE_ROLE_KEY>` | Secret service role key from Supabase |
   | `CINEFORGE_MANAGER_BOT_TOKEN` | `<YOUR_MANAGER_BOT_TOKEN_FROM_BOTFATHER>` | Bot API token for Manager Bot |
   | `CINEFORGE_MANAGER_BOT_USERNAME` | `<YOUR_MANAGER_BOT_USERNAME>` | e.g. `CineforgeManagerBot` (without `@`) |
   | `TELEGRAM_API_ID` | `<YOUR_TELEGRAM_API_ID_INTEGER>` | From my.telegram.org |
   | `TELEGRAM_API_HASH` | `<YOUR_TELEGRAM_API_HASH_HEX>` | From my.telegram.org |
6. Click **Create Web Service**.

### 5. What to Expect on the Free Tiers (Operational Nuances)

> [!NOTE]
> Understanding free-tier lifecycle behavior prevents confusing normal cloud platform sleep states with application bugs:
> 
> 1. **Render Free Web Service Sleep & Cold Starts**:
>    - Render Free services automatically spin down (sleep) after **15 minutes of inactivity**.
>    - When a user first opens Cineforge or clicks "Connect Telegram" while the provisioner is asleep, the initial HTTP request will wake up the container.
>    - This cold-start wakeup takes approximately **30 to 50 seconds**. During this time, the desktop app may show a brief loading state.
>    - Once the service is awake, all subsequent challenge, verification, and token operations respond in milliseconds.
>    - The provisioner remains awake as long as requests continue within each 15-minute window.
> 
> 2. **Supabase Free Tier Project Pausing**:
>    - Supabase Free tier projects are automatically paused if they experience **7 consecutive days of zero database activity**.
>    - If your project becomes paused after a period of non-use, opening Cineforge will return a `503 Service Unavailable` error when trying to look up bot mappings.
>    - You can unpause your database in seconds by clicking **Restore Project** in the [Supabase Dashboard](https://supabase.com/dashboard). Occasional usage of Cineforge keeps the database active indefinitely.

### 6. Verifying Deployment Health
Once Render completes building the Docker container:
1. Open `https://<your-service-name>.onrender.com/health` in your browser.
   - Expected response (HTTP 200 OK):
     ```json
     {
       "layer": 233,
       "service": "cineforge-provisioner",
       "status": "ok"
     }
     ```
2. Open `https://<your-service-name>.onrender.com/` in your browser.
   - Expected response (HTTP 200 OK):
     ```json
     {
       "health": "/health",
       "layer": 233,
       "service": "cineforge-provisioner",
       "status": "online"
     }
     ```
3. Check Render deployment logs:
   ```text
   Cineforge Bot Provisioner listening on http://0.0.0.0:10000 (dev_mode=false)
   Configuring SupabaseBotStore for durable bot mappings: https://<project>.supabase.co
   Connecting manager bot to MTProto...
   Manager bot successfully signed in as @<your_manager_bot_username>
   ```

### 7. Remaining Checklist & Blockers Before Live Launch
1. [ ] **Manager Bot Creation**: Talk to `@BotFather` on Telegram, create the Manager Bot (e.g. `@CineforgeManagerBot`), and record its token.
2. [ ] **Enable Bot Management Mode**: In `@BotFather`, run `/mybots` → select your Manager Bot → **Bot Settings** → **Bot Management** → **Turn On**.
3. [ ] **Telegram App Credentials**: Obtain valid `api_id` and `api_hash` from `my.telegram.org`.
4. [ ] **Supabase Table Migration**: Run `supabase/migrations/20261122_managed_bots.sql` in the Supabase SQL Editor.
5. [ ] **Render Free Service Deployment**: Deploy `cineforge-provisioner` on the Free tier and set the 8 private environment variables.
6. [x] **Client Connection**: Configured default provisioning service URL to `https://cineforge-provisioner.onrender.com` (can be overridden via `PROVISIONING_SERVICE_URL`).


