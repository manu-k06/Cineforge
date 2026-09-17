# Deploying Cineforge Go Streamer to Render

This guide walks you through deploying the high-concurrency Go Telegram file streamer to [Render](https://render.com) as a cloud web service.

---

## Architecture Overview

```
 [ Browser / Video Player ]
           │
           │ Range Requests (HTTP 206)
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Render Web Service (Cineforge Go Streamer)                 │
│  https://cineforge-streamer.onrender.com                     │
│                                                             │
│  • Binds to 0.0.0.0:$PORT                                   │
│  • Health Check: /health                                    │
│  • Multi-DC Connection Pool                                 │
│  • High-Throughput MTProto Pipe (gotd/td)                   │
└─────────────────────────────────────────────────────────────┘
           │
           │ MTProto TCP (TLS)
           ▼
    [ Telegram DC 1-5 Servers ]
```

---

## Prerequisites & Secrets

Before deploying, ensure you have the following credentials ready:

| Variable | Description | Example / Location |
| :--- | :--- | :--- |
| `TELEGRAM_API_ID` | Telegram App API ID | Numeric ID from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | Telegram App API Hash | 32-character hex hash from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_SESSION_STRING` | Telethon Session String | String from `streamer/session.txt` |
| `STREAM_SECRET_KEY` | *(Optional)* HMAC-SHA256 secret | Shared token secret (leave blank to bypass verification) |

> [!TIP]
> **How to get your Telethon Session String**:
> If you already generated a session locally, open `streamer/session.txt` and copy its single-line string content.

---

## Deployment Methods

### Method 1: 1-Click Render Blueprint (Recommended)

Render Blueprints let you deploy infrastructure declaratively using the included [render.yaml](file:///c:/Users/manuk/Downloads/projects/Cineforge/render.yaml).

1. Push your repository to GitHub / GitLab:
   ```bash
   git add .
   git commit -m "feat: add Render deployment support for Go streamer"
   git push origin main
   ```
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** in the top navigation bar and select **Blueprint**.
4. Connect your **Cineforge** repository.
5. Render will automatically detect `render.yaml`.
6. Enter your secret environment variables when prompted:
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`
   - `TELEGRAM_SESSION_STRING`
   - `STREAM_SECRET_KEY` (optional)
7. Click **Apply**. Render will build the Docker container and deploy the streamer service!

---

### Method 2: Manual Web Service Setup (Docker)

If you prefer configuring the service manually through the Render UI:

1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your Git repository.
3. Configure the following service settings:
   - **Name**: `cineforge-streamer`
   - **Region**: Select closest to your primary Telegram DC (e.g. *Frankfurt* for DC2/DC4, or *Oregon/Ohio* for US)
   - **Branch**: `main`
   - **Root Directory**: *(leave blank)*
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./streamer/Dockerfile`
   - **Docker Build Context**: `./streamer`
   - **Instance Type**: **Free** (or **Starter** for zero cold-starts)
4. Under **Advanced** settings:
   - **Health Check Path**: `/health`
5. Under **Environment Variables**, add:
   - `HOST` = `0.0.0.0`
   - `PORT` = `10000`
   - `TELEGRAM_API_ID` = `<your_api_id>`
   - `TELEGRAM_API_HASH` = `<your_api_hash>`
   - `TELEGRAM_SESSION_STRING` = `<your_session_string>`
   - `STREAM_SECRET_KEY` = `<your_optional_secret_key>`
6. Click **Create Web Service**.

---

### Method 3: Native Go Runtime on Render

Render also supports building directly from Go source without Docker:

1. Click **New +** → **Web Service** and connect your repo.
2. Select **Go** runtime.
3. Configure:
   - **Root Directory**: `streamer`
   - **Build Command**:
     ```bash
     go build -ldflags="-s -w" -o streamer main.go telegram.go pool.go pipe.go range.go auth.go
     ```
   - **Start Command**:
     ```bash
     ./streamer
     ```
   - **Health Check Path**: `/health`
4. Add the same Environment Variables as in Method 2.

---

## Verifying Your Deployment

Once Render finishes building, your service will receive a public HTTPS URL:
`https://<your-service-name>.onrender.com`

### 1. Test Health Endpoint
```bash
curl -i https://<your-service-name>.onrender.com/health
```
Expected response:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"healthy","service":"cineforge-streamer","engine":"gotd/td"}
```

### 2. Test Range Streaming
Request the first 1 MB of a Telegram file via message ID:
```bash
curl -i -r 0-1048575 https://<your-service-name>.onrender.com/stream/me/<message_id>
```
Expected response:
```http
HTTP/1.1 206 Partial Content
Content-Type: video/mp4
Content-Range: bytes 0-1048575/<total_size>
Accept-Ranges: bytes
```

---

## Connecting Cineforge Backend to Render Streamer

Once your Render Go Streamer is running, configure your FastAPI backend to route video stream URLs to Render instead of localhost.

In your backend `.env` file (e.g. `backend/.env`):
```env
# Point directly to your Render public service URL:
STREAMER_BASE_URL="https://<your-service-name>.onrender.com"

# If STREAM_SECRET_KEY was configured on Render, match it here:
STREAM_SECRET_KEY="your-secret-key-if-configured"
```

When users request search results or playback links, the backend will automatically generate authoritative stream URLs targeting your high-speed Render cloud streamer!

---

## Free vs. Starter Tier Considerations

- **Render Free Tier**:
  - Automatically spins down after **15 minutes** of zero traffic.
  - The first stream request after inactivity takes ~50 seconds to boot the container and reconnect to MTProto.
- **Render Starter Tier ($7/mo)**:
  - Runs 24/7 without cold starts.
  - Keeps persistent MTProto ping connections active continuously for instant playback.
