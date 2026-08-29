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

## Milestone B6: HTTP Range Streaming Endpoints & Testing

### Step 1: Create a Media Streaming Session
- **Endpoint**: `POST /api/media/session`
- **PowerShell Command**:
```powershell
$session = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session" -Method POST -ContentType "application/json" -Body '{"message_id": 12580}'
$session | ConvertTo-Json -Depth 5
$sessionId = $session.session_id
```
- **Example Response**:
```json
{
  "session_id": "a4d3e210-9c4b-4df2-a94f-561234abcde5",
  "file_name": "Inception.2010.3D.Multi.Audio[@Dubbedmovies].mkv",
  "mime_type": "video/x-matroska",
  "size": 1125702788,
  "stream_url": "/api/media/stream/a4d3e210-9c4b-4df2-a94f-561234abcde5"
}
```

---

### Step 2: Test HTTP Range Request (First 1 MB)
- **Endpoint**: `GET /api/media/stream/{session_id}`
- **curl.exe with Range Header**:
```powershell
curl.exe -i -H "Range: bytes=0-1048575" "http://127.0.0.1:8000/api/media/stream/$sessionId" --output test_1mb.part
```
- **Expected Headers**:
```http
HTTP/1.1 206 Partial Content
accept-ranges: bytes
content-range: bytes 0-1048575/1125702788
content-length: 1048576
content-type: video/x-matroska
```

---

### Step 3: Test Non-Zero Seek Range (500 MB Offset)
- **PowerShell / curl.exe Command**:
```powershell
curl.exe -i -H "Range: bytes=524288000-528482303" "http://127.0.0.1:8000/api/media/stream/$sessionId" --output seek_4mb.part
```
- **Expected Headers**:
```http
HTTP/1.1 206 Partial Content
accept-ranges: bytes
content-range: bytes 524288000-528482303/1125702788
content-length: 4194304
```

---

### Step 4: Test Cache Hit by Repeating the Same Range
- **PowerShell Benchmark Endpoint**:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/benchmark-stream/$sessionId?start=0&end=4194303" | ConvertTo-Json -Depth 5
```
*(Notice `cache_hit: true` and latency dropping to $< 5\text{ms}$ on repeat)*.

---

### Step 5: Test Invalid Range (Expect 416 Range Not Satisfiable)
```powershell
curl.exe -i -H "Range: bytes=2000000000-2000100000" "http://127.0.0.1:8000/api/media/stream/$sessionId"
```
- **Expected Status**: `416 Range Not Satisfiable` with `Content-Range: bytes */1125702788`.

---

### Step 6: Inspect Session Observability & Memory Metrics
- **Endpoint**: `GET /api/media/session/{session_id}`
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session/$sessionId" | ConvertTo-Json -Depth 5
```
- **Example Response**:
```json
{
  "session_id": "a4d3e210-9c4b-4df2-a94f-561234abcde5",
  "file_name": "Inception.2010.3D.Multi.Audio[@Dubbedmovies].mkv",
  "file_size_bytes": 1125702788,
  "cached_chunks_count": 8,
  "cached_bytes": 4194304,
  "max_buffer_bytes": 16777216,
  "cache_hits": 6,
  "cache_misses": 8,
  "cache_hit_ratio": 0.429,
  "total_bytes_served": 12582912,
  "last_requested_range": "bytes=0-4194303",
  "created_at": 1724912000.0,
  "last_accessed_at": 1724912065.0
}
```

---

### Step 7: Explicit Session Cleanup
- **Endpoint**: `DELETE /api/media/session/{session_id}`
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session/$sessionId" -Method DELETE | ConvertTo-Json -Depth 5
```
