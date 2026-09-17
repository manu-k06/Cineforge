# Milestone B9 — Browser Playback Architecture Specification

## 1. Executive Summary & Recommended Architecture

### Core Problem
Cineforge has completed Milestones B1 through B8, establishing high-performance Telegram MTProto media retrieval, chunk-based session caching (512 KB blocks, 16 MB bounded LRU), RFC 7233 HTTP Range streaming, media probing (FFprobe), and real-time playback viability tracking (`BufferHealthEngine`).

However, milestone B7 probing established that real-world media files delivered via Telegram commonly use the **Matroska (`.mkv`) container** with **H.264 (AVC) video** and **MP3 or AAC (or AC3/E-AC3/DTS) audio**. Modern desktop and mobile web browsers (Chrome, Firefox, Safari, Edge) do **not** natively support the MKV container in standard HTML5 `<video>` elements, even when the underlying H.264 and MP3/AAC streams are 100% codec-compatible.

### Recommendation: Server-Assisted On-Demand Progressive fMP4 Remuxing with Video.js (MSE) & Audio Passthrough/Fallback

We recommend an **On-the-Fly Progressive Fragmented MP4 (fMP4) Remuxing Pipeline** using lightweight stream-copy (`-c:v copy`) layered directly on the existing `MediaStreamSession` and B8 `BufferHealthEngine`.

```
┌─────────────────┐       MTProto Chunks (512 KB)       ┌──────────────────────────────┐
│ Telegram Cloud  │ ─────────────────────────────────>  │  MediaStreamSession (B6)     │
│ (DC2 / DC4)     │                                     │  • 16 MB LRU Chunk Cache     │
└─────────────────┘                                     │  • B8 Throughput Estimator   │
                                                        └──────────────┬───────────────┘
                                                                       │ Sliced byte spans
                                                                       ▼
┌─────────────────┐       Fragmented MP4 (fMP4)         ┌──────────────────────────────┐
│ Browser Client  │ <─────────────────────────────────  │  FastAPI Stream Route (B9)   │
│ Video.js + MSE  │     (moov + moof/mdat fragments)    │  • FFmpeg stream-copy pipe   │
│ • Custom UI     │                                     │  • Range/Time seeking        │
│ • Buffer UI     │                                     │  • Zero-copy H.264 passthru  │
└─────────────────┘                                     └──────────────────────────────┘
```

#### Why this is the winning architecture:
1. **100% Browser Compatibility**: Output is standard ISO Base Media File Format (ISOBMFF / fMP4) supported natively by all modern browsers via HTML5 `<video>` and Media Source Extensions (MSE).
2. **Instant Startup (< 1.5s)**: Only the first 1–2 MB of the MKV (header + first keyframe) is fetched to emit the initial fMP4 `ftyp` + `moov` initialization segment. Playback starts immediately without waiting for the full 1.1 GB file.
3. **Near-Zero Server CPU (< 1% CPU utilization)**: Video is **never re-encoded** (`-c:v copy`). Video packets (NAL units) are simply re-encapsulated from Matroska EBML blocks into MP4 `moof`/`mdat` atom boxes.
4. **Seamless Seeking**: Time-based and byte-based seeking requests are translated into precise MKV keyframe offsets via `MediaStreamSession`, resetting the stream pipeline cleanly at the target keyframe.
5. **Full B8 Integration**: The remuxer reads MKV bytes exclusively through `MediaStreamSession.get_chunk()`, ensuring `ThroughputEstimator`, `BufferHealthEngine`, and adaptive prefetching continue to operate with full fidelity.
6. **Robust Audio Handling**: Codec passthrough (`-c:a copy`) for native MP3/AAC; instant lightweight audio transcoding (`-c:a aac -b:a 192k`) only if unsupported audio like AC3, DTS, or TrueHD is detected.

---

## 2. Current B1–B8 Streaming Architecture

The current backend architecture consists of:
* **Telegram MTProto Client (`telegram_service`)**: Connects as a user session to Telegram DCs, executing chunked file downloads in standard 512 KB blocks.
* **`TelegramMediaReader`**: Resolves media documents, manages message references, and fetches arbitrary byte ranges `[start, end]`.
* **`MediaStreamSession` & `MediaChunkCache` (B6)**: Isolated per-session LRU cache with an upper memory limit (default 16 MB). Request deduplication prevents redundant Telegram fetches.
* **HTTP Range Endpoint (`/api/media/stream/{session_id}`)**: Implements RFC 7233 HTTP 206 Partial Content and 416 Range Not Satisfiable.
* **Probing & Compatibility Engine (`MediaProbeService`, B7)**: Uses FFprobe over the first 2 MB to extract container, video codec, audio codec, dimensions, frame rate, duration, and calculate sustainability ratios.
* **Buffer Health Engine (`BufferHealthEngine` & `ThroughputEstimator`, B8)**: Dynamic throughput tracking via a sliding window, playback drain rate calculation, buffer duration in seconds, health states (`HEALTHY`, `LOW`, `CRITICAL`, `STALLED`), time-to-stall estimation, and adaptive prefetch decision scaling (`PAUSE_PREFETCH`, `NORMAL_PREFETCH`, `AGGRESSIVE_PREFETCH`, `STALL_WARNING`).

---

## 3. Why MKV Cannot Be Given Directly to HTML5 Video / Video.js

1. **Browser Container Support**:
   * Standard HTML5 `<video>` and browser MSE engines natively parse **MP4 (ISO BMFF)** and **WebM (subset of Matroska)**.
   * Full **Matroska (`.mkv`)** uses complex EBML schemas with arbitrary codec track IDs, variable header structures, and subtitle overlays that browser media decoders (like Chrome's Blink media pipeline or Safari's AVFoundation) explicitly reject.
2. **Direct `<video src=".../stream/{id}">` Failure**:
   * When an MKV stream URL is assigned to `video.src`, the browser reads the initial magic bytes (`0x1A 0x45 0xDF 0xA3` EBML Header). Chrome immediately emits `MEDIA_ERR_SRC_NOT_SUPPORTED` (Format error) and aborts playback, despite the H.264 stream inside being completely standard.
3. **Player Abstraction Limits**:
   * Video.js is a wrapper around the browser's native `<video>` element and MSE pipeline. Video.js cannot magically play a format if the browser's underlying media stack or MSE SourceBuffer cannot demux the container.

---

## 4. Remuxing Feasibility & Progressive Pipeline

### Transcoding vs. Remuxing (Stream Copy)
| Dimension | Video Transcoding (`libx264`) | Video Remuxing / Transmuxing (`-c:v copy`) |
| :--- | :--- | :--- |
| **CPU Usage** | 80% – 100% across multiple cores | < 1% CPU (I/O bound memory copy) |
| **Throughput Speed** | ~0.5× – 1.5× realtime (slow) | 50× – 200× realtime (instant) |
| **Latency to First Frame** | 5 – 15 seconds | 0.2 – 0.5 seconds |
| **Video Quality** | Generates compression artifacts / quality loss | 100% Bit-exact lossless original |
| **Memory Footprint** | Large frame buffers (100–300 MB) | Small packet buffers (< 10 MB) |

### Why Standard MP4 Fails for Live/Progressive Streaming
* A standard MP4 file requires a `moov` atom that indexes every sample's offset in the `mdat` block.
* Generating a standard `moov` atom with `-movflags +faststart` requires reading the **entire** 1.1 GB file before the first byte of MP4 can be sent to the browser.
* This would cause a **2.4-hour startup delay** on a 1.05 Mbps connection.

### The Solution: Fragmented MP4 (fMP4)
* Fragmented MP4 splits the stream into:
  1. **Initialization Segment**: `ftyp` (file type) + `moov` (track definitions, codec parameters, SPS/PPS for H.264). This requires only the first ~1–2 MB of the MKV.
  2. **Media Fragments**: Continuous series of `moof` (movie fragment header with timestamps) + `mdat` (video/audio NAL units). Each fragment can represent 1–4 seconds of video.
* `ffmpeg` command for on-the-fly progressive fMP4 remux:
  ```bash
  ffmpeg -loglevel error \
    -i pipe:0 \
    -c:v copy \
    -c:a copy \
    -movflags frag_keyframe+empty_moov+default_base_moof \
    -f mp4 \
    pipe:1
  ```
* If audio is unsupported (e.g. AC3/DTS):
  ```bash
  ffmpeg -loglevel error \
    -i pipe:0 \
    -c:v copy \
    -c:a aac -b:a 192k \
    -movflags frag_keyframe+empty_moov+default_base_moof \
    -f mp4 \
    pipe:1
  ```
  *(Audio transcoding to AAC requires negligible CPU compared to video, ~1–2% single-core).*

---

## 5. Architectural Comparison of Viable Approaches

| Criteria (Priority Order) | Option 1: On-the-Fly Progressive fMP4 Stream (Recommended) | Option 2: Dynamic Segmented HLS (`.m3u8` / `.m4s`) | Option 3: Client-Side JS/WASM Transmuxer (MSE + Web Worker) | Option 4: Full Offline Transcoding to MP4 |
| :--- | :--- | :--- | :--- | :--- |
| **1. Browser Compatibility** | **Excellent (100%)** via HTML5 `<video>` / MSE | **Excellent (100%)** via Video.js / VHS | **Good (85%)** — fails on non-AAC/MP3 audio | **Excellent (100%)** |
| **2. Fast Startup Latency** | **Fastest (< 1.5s)**: First chunk generates `moov` + 1st `moof` | **Medium (2–4s)**: Requires manifest parse + segment load | **Fast (1.5–2s)**: Reads EBML header in JS | **Unacceptable (> 2 hours)**: Must transcode entire file |
| **3. Bandwidth Efficiency** | **High**: Only requested byte ranges fetched from Telegram | **High**: Fetches only requested segment ranges | **High**: Pure byte ranges | **Extremely Poor**: Downloads 100% of movie upfront |
| **4. Seeking Support** | **Clean**: Query parameter `?t={seconds}` resets remuxer at target keyframe | **Native**: Seek bar jumps to specific segment index | **Complex**: JS must parse MKV Cues to find byte offsets | **Native**: Standard MP4 byte ranges |
| **5. B8 Buffering Integration** | **Direct**: Remuxer reads from `MediaStreamSession`, updating metrics | **Direct**: Each segment read passes through `MediaStreamSession` | **Direct**: Raw byte ranges go to B6/B8 endpoint | **None during playback** (offline task) |
| **6. Server CPU Usage** | **Negligible (< 1%)**: Zero-copy video remux | **Low (1–3%)**: Spawned segment remux | **Zero (0%)**: All demuxing in browser | **Massive (100%)**: Multi-core CPU saturation |
| **7. Long Movies (2.5+ hrs)** | **Rock solid**: Infinite fragment streaming | **Rock solid**: Infinite segment sequence | **Risk of JS memory leaks / GC pressure** | **Rock solid** |

---

## 6. Detailed Design: How Telegram Chunks Map to Browser Playback

```
Telegram MTProto Blocks (512 KB)
[Chunk 0][Chunk 1][Chunk 2][Chunk 3][Chunk 4] ... [Chunk N]
    │        │        │        │
    ▼        ▼        ▼        ▼
MediaStreamSession LRU Memory Cache (16 MB Bounded)
    │
    ▼ Async Reader Pipe
[FFmpeg Process: -c:v copy -movflags frag_keyframe+empty_moov+default_base_moof]
    │
    ├─► Segment 0: [ftyp + moov] (Initialization ~4 KB)
    ├─► Fragment 1: [moof + mdat] (Keyframe + GOP ~500 KB)
    ├─► Fragment 2: [moof + mdat] (GOP ~400 KB)
    ▼
FastAPI StreamingResponse (media_type="video/mp4")
    │
    ▼ HTTP Stream
Browser HTML5 <video> / Video.js (MSE SourceBuffer)
```

### Chunk Flow Mechanics
1. Client requests playback: `GET /api/media/session/{session_id}/play.mp4?t=0`.
2. Backend initiates a reader stream fed from `MediaStreamSession.stream_byte_range()`.
3. The reader stream pipes raw MKV data directly into `ffmpeg.stdin`.
4. As `ffmpeg` processes packets, it emits:
   * Header atoms (`ftyp`, `moov`) within the first 100 ms.
   * `moof` + `mdat` fragments as soon as each video GOP (Group of Pictures / keyframe interval) is completed.
5. FastAPI streams these MP4 bytes over HTTP with `Transfer-Encoding: chunked` and `Content-Type: video/mp4`.
6. Browser immediately begins decoding and displaying frames.

---

## 7. Seeking Architecture & Workflow

### Time-Based Seeking Flow
```
User drags Video.js seek bar to 01:15:00 (4500 seconds)
                   │
                   ▼
Video.js issues GET /api/media/session/{session_id}/play.mp4?t=4500
                   │
                   ▼
Backend calculates approximate byte offset from MKV bitrate/metadata:
Target Byte = (4500 / Duration) * TotalFileSize
                   │
                   ▼
FFmpeg started with fast input seek:
ffmpeg -ss 4500 -i <pipe/reader> -c:v copy -movflags frag_keyframe+empty_moov+default_base_moof
                   │
                   ▼
MediaStreamSession fetches chunks starting around keyframe boundary
                   │
                   ▼
New fMP4 initialization (moov) + fragments streamed to browser
                   │
                   ▼
Video.js displays video at 01:15:00 in < 1.0 second
```

---

## 8. Integration with B8 Buffering & Adaptive Prefetch

The B9 remuxing layer does not bypass `MediaStreamSession`. Instead, all reads by the remuxer worker flow through `session.get_chunk()` and `session.stream_byte_range()`.

* **Throughput Tracking**: Every 512 KB chunk fetched from Telegram records download duration in `ThroughputEstimator`.
* **LRU Cache Retention**: Chunks remain in `MediaChunkCache` so quick rewind seeks hit cache instantly.
* **Buffer Health Evaluation**: `BufferHealthEngine.evaluate_buffering()` calculates real-time buffer seconds, drain rate, and health states (`HEALTHY`, `LOW`, `CRITICAL`, `STALLED`).
* **Adaptive Prefetch**: If the buffer health drops to `LOW` or `CRITICAL`, `trigger_adaptive_prefetch()` automatically schedules background fetches for subsequent chunks ahead of the playhead.
* **Buffering API**: The frontend UI polls `GET /api/media/session/{session_id}/buffering` to render real-time buffer meters, speed indicators, and stall warnings on the custom player skin.

---

## 9. Frontend Video.js Integration Architecture

### Recommended Frontend Stack
* **Framework**: React / Modern HTML5
* **Player Core**: **Video.js v8+** with `@videojs/http-streaming`
* **Custom UI Components**:
  1. **Playback Viewport**: Standard responsive HTML5 video container.
  2. **Buffering Health Bar**: Dual-layer seekbar displaying:
     * Current playback position (seconds).
     * Server-side LRU buffer range (buffered seconds from B8 metrics).
     * Client-side MSE buffer range (`video.buffered`).
  3. **Stream Health Overlay**: Shows real-time MTProto download throughput, media drain rate, sustainability indicator, and stall alerts.

```html
<video
  id="cineforge-player"
  class="video-js vjs-big-play-centered vjs-theme-cineforge"
  controls
  preload="auto"
  width="1280"
  height="720"
  data-setup='{"fluid": true, "liveui": false}'
>
  <source src="/api/media/session/{session_id}/play.mp4" type="video/mp4" />
</video>
```

---

## 10. Failure & Recovery Behavior

1. **Telegram Rate Limiting / FloodWait**:
   * If Telegram returns `FloodWaitError` or temporary timeout on a chunk, `MediaStreamSession` retries with exponential backoff while serving existing buffered chunks from the 16 MB LRU cache.
   * `BufferHealthEngine` transitions health state to `CRITICAL` / `STALLED`, notifying frontend UI to show buffering spinner before playback freezes.
2. **Subprocess / FFmpeg Error**:
   * If FFmpeg encounters corrupt container packets, it logs the error without crashing the server process. FastAPI terminates the `StreamingResponse` gracefully, triggering Video.js client retry at the last known timestamp.
3. **Client Disconnect**:
   * When user closes the browser tab or seeks to another position, FastAPI detects `ClientDisconnected` / `asyncio.CancelledError`, immediately terminating the FFmpeg subprocess and canceling any pending prefetch tasks.

---

## 11. CPU, Memory & Resource Budget

* **Server CPU Utilization**:
  * Single 1080p stream remuxing: **< 1.5% CPU core usage**.
  * 10 concurrent streams: **< 15% single multi-core CPU**.
* **Server Memory Utilization**:
  * Bounded cache: **16 MB** per active session.
  * FFmpeg pipe buffer: **~4 MB** per active stream.
  * Total memory for 10 active sessions: **~200 MB RAM** (extremely lightweight).
* **Client Performance**:
  * Hardware-accelerated H.264 decoding in browser GPU/VPU.
  * Battery efficient on mobile/laptops compared to software decoding.

---

## 12. Recommended B9 Implementation Phases

### Phase 1: Core Progressive Remuxing Engine (`app/services/remux.py`)
* Implement async subprocess pipe manager wrapping FFmpeg with stream copy `-c:v copy`.
* Detect audio format from B7 metadata: use `-c:a copy` for MP3/AAC; use `-c:a aac -b:a 192k` for AC3/DTS/EAC3.
* Package output into fMP4 (`frag_keyframe+empty_moov+default_base_moof`).

### Phase 2: Playback Streaming API Route (`app/api/stream.py`)
* Add `GET /api/media/session/{session_id}/play.mp4`.
* Support timestamp seeking query parameter `?t={seconds}` and standard Range header handling.
* Ensure clean process cleanup on client disconnect.

### Phase 3: Automated Test Suite (`tests/test_b9_remux.py`)
* Test fMP4 header generation (`ftyp`/`moov` atom validation).
* Test audio codec passthrough vs audio fallback transcoding.
* Test fast startup (< 1.5s for initial packets).
* Test seek stream initialization at timestamp offset.
* Regression test B1–B8 endpoints.

### Phase 4: Frontend Video Player Integration
* Mount Video.js player component connected to `/api/media/session/{session_id}/play.mp4`.
* Integrate B8 buffering metrics polling for dynamic player status overlay.
