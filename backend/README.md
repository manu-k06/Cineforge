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
   - **`MediaProbeService`**: Inspects container format, streams, and codecs using bundled binary inspection.
   - **HTML5 Browser Compatibility Assessment**: Reasoned evaluation of container and codec browser playability.
   - **Playback Sustainability Analysis**: Compares measured source throughput against media bitrate with safety margin.
   - **Buffer Capacity & Strategy Recommendation**: Computes max buffer hold time and recommends optimal buffering strategy.
6. **Playback Viability & Buffering Layer (Milestone B8)**:
   - **`ThroughputEstimator`**: Sliding window estimator of real chunk download speeds.
   - **`BufferHealthEngine`**: State machine (`HEALTHY`, `LOW`, `CRITICAL`, `STALLED`), playback drain rate, and time-to-stall calculations.
   - **Adaptive Prefetch Decision**: Dynamically scales prefetch chunks (0 to 4) based on buffer health and pauses when buffer is saturated.
   - **Buffering Metrics Endpoint**: `GET /api/media/session/{session_id}/buffering`.

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

## Running Automated Tests

Run the complete unittest & regression test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## Milestone B8: Live Testing Commands

### 1. Create a Streaming Session
```powershell
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session" -Method POST -ContentType "application/json" -Body '{"message_id": 12580}'
$sessionId = $resp.session_id
Write-Host "Active Session ID: $sessionId" -ForegroundColor Green
```

---

### 2. View Real-Time Buffering Health & Viability Metrics
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session/$sessionId/buffering" | ConvertTo-Json -Depth 8
```

---

### 3. View Probed Metadata & Compatibility (B7)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/media/session/$sessionId/metadata" | ConvertTo-Json -Depth 8
```

---

### 4. Stream Byte Range (B6 Regression)
```powershell
curl.exe -D test.headers -H "Range: bytes=0-1048575" "http://127.0.0.1:8000/api/media/stream/$sessionId" -o test_1mb.part
(Get-Item test_1mb.part).Length
```
*(Must output `1048576`)*.

---

### 5. Interactive Swagger Documentation
- **URL**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
