# Cineforge Backend

Backend service for the Cineforge personal movie streaming web application.

---

## Architecture Overview

Cineforge uses an authenticated Telegram **User Account** via Telethon (MTProto) for high-performance, on-demand video access:

1. **Movie Search**: Direct private chat search with the movie bot returning structured titles, qualities, and deep links.
2. **Automated FSub & Channel Join**: Automatically joins updates channels in the background and resolves gatekeeper verification.
3. **High-Performance Media Access & Diagnostics (B5 / B5.2)**:
   - **`TelegramMediaReader`**: Memory-bounded reader using MTProto 512 KB chunk streaming.
   - **Performance Profiling**: Validated real MTProto upstream throughput and media bitrate calculations.
4. **Adaptive Media Buffer & HTTP Range Streaming (Milestone B6)**:
   - **`MediaStreamSession`**: Per-viewer isolated streaming session with unique UUID.
   - **`MediaChunkCache`**: Bounded LRU memory cache (16 MB cap per session) storing 512 KB Telegram chunks.
   - **Adaptive Byte-Range Prefetching**: Prefetches the next 1–2 chunks ahead of current playhead.
   - **RFC 7233 HTTP Range Endpoint (`206 Partial Content`)**: Enables browser video seeking directly at non-zero offsets without loading preceding bytes.
   - **Request Deduplication & Cancellation**: Protects against duplicate chunk fetches and cleans up background workers upon client disconnect.
5. **Media Probing, Compatibility & Playback Sustainability (Milestone B7)**:
   - **`MediaProbeService`**: Inspects container format, streams, and codecs using `ffprobe` (or graceful Telegram metadata fallback if ffprobe is absent).
   - **HTML5 Browser Compatibility Assessment**: Reasoned evaluation of container and codec browser playability.
   - **Playback Sustainability Analysis**: Compares measured source throughput against media bitrate with safety margin.
   - **Buffer Capacity & Strategy Recommendation**: Computes max buffer hold time and recommends optimal buffering strategy (`realtime`, `conservative_prefetch`, `aggressive_prefetch`, or `unsustainable`).

---

## Requirements

- **Python Version**: Python 3.12+ (Tested with Python 3.12+)

---

## Setup Instructions (Windows PowerShell)

### 1. Navigate to the Backend Directory
```powershell
cd backend
```

### 2. Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure `.env`
```powershell
Copy-Item .env.example .env
```

Key configuration variables:
- `TELEGRAM_API_ID`: Your API ID from [my.telegram.org](https://my.telegram.org)
- `TELEGRAM_API_HASH`: Your API Hash from [my.telegram.org](https://my.telegram.org)
- `TELEGRAM_SESSION_NAME`: Defaults to `cineforge_session`
- `TELEGRAM_BOT_USERNAME`: Third-party movie search bot username (e.g. `Spoty_xbot`)
- `TELEGRAM_CHUNK_SIZE`: 524288 (512 KB, MTProto standard max request chunk)
- `MEDIA_MAX_BUFFER_MB`: 16 (16 MB LRU cache limit per streaming session)
- `MEDIA_SESSION_TIMEOUT`: 600 (10 minutes inactivity timeout)
- `MEDIA_PREFETCH_CHUNKS_AHEAD`: 2 (Prefetch 2 chunks = 1 MB ahead)
- `FFPROBE_PATH`: `ffprobe` (or path to ffprobe executable)
- `MEDIA_SUSTAINABILITY_MARGIN`: 1.15
- `MEASURED_SOURCE_THROUGHPUT_BPS`: 1050000

---

## Telegram Authentication Workflow

Run the interactive login script:

```powershell
python login.py
```
*(Or `.\.venv\Scripts\python.exe login.py`)*

Choose **Option 1 (QR Code)**:
1. Scan the terminal QR code from your phone's Telegram app:
   **Settings $\rightarrow$ Devices $\rightarrow$ Link Desktop Device**.
2. Once authenticated, `cineforge_session.session` is saved.

---

## Starting the FastAPI Server

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Milestone B7: Media Probing & Compatibility Testing

### 1. Create a Streaming Session
```powershell
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session" -Method POST -ContentType "application/json" -Body '{"message_id": 12580}'
$sessionId = $resp.session_id
Write-Host "Active Session ID: $sessionId" -ForegroundColor Green
```

---

### 2. Inspect Probed Metadata, Compatibility & Sustainability
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session/$sessionId/metadata" | ConvertTo-Json -Depth 8
```

---

### 3. B6 HTTP Range Regression Verification

#### Test A: 1 MB Range (Expect 206 and 1,048,576 Bytes)
```powershell
curl.exe -D test.headers -H "Range: bytes=0-1048575" "http://127.0.0.1:8000/api/media/stream/$sessionId" -o test_1mb.part
(Get-Item test_1mb.part).Length
```
*(Must output `1048576`)*.

#### Test B: Non-Zero 4 MB Seek Range (Expect 206 and 4,194,304 Bytes)
```powershell
curl.exe -D seek.headers -H "Range: bytes=524288000-528482303" "http://127.0.0.1:8000/api/media/stream/$sessionId" -o seek_4mb.part
(Get-Item seek_4mb.part).Length
```
*(Must output `4194304`)*.

---

### 4. Interactive Swagger Documentation
- **URL**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
