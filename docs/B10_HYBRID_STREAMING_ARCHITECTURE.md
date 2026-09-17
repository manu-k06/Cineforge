> [!NOTE]
> **Historical Archive**: The HLS architecture specified in this document has been completely removed in Phase 14 in favor of the direct Go streamer architecture (for MP4/WebM) and progressive FFmpeg stream-copy fMP4 remuxing (for MKV/incompatible formats). HLS endpoints (`/master.m3u8`, `/segment/{idx}.mp4`) and HLS services are no longer part of Cineforge.

## 1. Executive Summary & Architecture Overview

### Background & Evolution
* **B6**: Implemented RFC 7233 HTTP 206 Partial Content range streaming over 512 KB MTProto chunked blocks with a 16 MB bounded LRU memory cache.
* **B7**: Added FFprobe media inspection, container/codec probing, and sustainability metrics ($S = \text{Throughput} / (\text{Bitrate} \times 1.15)$).
* **B8**: Introduced the dynamic `BufferHealthEngine`, real-time sliding-window `ThroughputEstimator`, time-to-stall estimation, and buffer health states (`HEALTHY`, `LOW`, `CRITICAL`, `STALLED`).
* **B9**: Introduced continuous progressive fragmented MP4 (fMP4) remuxing with zero video transcoding (`-c:v copy`), browser audio compatibility (AAC fallback), and Video.js 8+ integration.

### The B10 Hybrid Segmented Architecture
Milestone B10 evolves Cineforge from a single continuous progressive pipe to a **hybrid segmented streaming architecture** based on:
1. **Independently Addressable fMP4 Segments** delivered over HLS/fMP4 with standard media playlists (`master.m3u8`).
2. **Adaptive Time-Based Initial Prebuffering** governed by B8 throughput and sustainability ratios before initiating playback.
3. **Bounded Segment LRU Cache** (`BoundedSegmentCache`) with concurrent request deduplication to prevent redundant FFmpeg invocations.
4. **Intelligent Background Prefetching** (`BackgroundPrefetchManager`) that dynamically paces forward segment generation according to B8 buffer health.
5. **Fast Non-Linear Seeking** that maps timestamps directly to segment indices, checking segment cache and fetching only the required region without downloading intermediary segments.
6. **Full Backward Compatibility**: Preserves B9 progressive `/play.mp4` and B6 `/stream/{id}` range streaming untouched as robust fallbacks.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Telegram Cloud (DC2 / DC4)                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ MTProto 512 KB chunks (on-demand)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   MediaStreamSession & MediaChunkCache                  │
│                     (16 MB Bounded Raw MKV LRU)                         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Sliced byte reads via pipe
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       SegmentService (FFmpeg)                           │
│     • Fast input seek (-ss) • Stream copy (-c:v copy)                   │
│     • Audio passthrough (AAC/MP3) or AAC fallback                       │
│     • Independent fMP4 output (frag_keyframe+empty_moov)                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Generated fMP4 segment bytes
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   BoundedSegmentCache (64 MB LRU)                       │
│     • In-flight generation deduplication (asyncio.Future)               │
│     • Hits served instantly (< 10ms)                                    │
└──────────┬─────────────────────────┬─────────────────────────┬──────────┘
           │                         │                         │
           ▼                         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│AdaptivePrebuffer     │  │BackgroundPrefetch    │  │HLS Delivery Router   │
│Engine                │  │Manager               │  │• master.m3u8         │
│• B8 Sustainability   │  │• B8 Health Pacing    │  │• segment_{idx}.mp4   │
│• Dynamic prebuffer   │  │• Seek realignment    │  │• prebuffer metrics   │
└──────────────────────┘  └──────────────────────┘  └──────────┬───────────┘
                                                               │
                                                               ▼
                                                    ┌──────────────────────┐
                                                    │ Video.js 8+ Player   │
                                                    │ • HLS Streaming (VHS)│
                                                    │ • B8 Telemetry UI    │
                                                    │ • B9 Fallback Mode   │
                                                    └──────────────────────┘
```

---

## 2. Technical Validation of Critical Assumptions

### 2.1 Timestamp → MKV Source-Byte-Range Mapping Validation
**Question**: Can a target timestamp region be extracted from Telegram without downloading the entire file?

**Analysis & Findings**:
1. In Matroska (`.mkv`) files, EBML track headers and codec initialization parameters (SPS/PPS) reside at the very beginning of the container (bytes 0 to ~2 MB).
2. Arbitrary non-linear seeks in MKV without the initial EBML header cause raw demuxers to fail to identify stream tracks unless the initial header is provided.
3. However, `MediaStreamSession` caches chunks in 512 KB blocks. When FFmpeg is invoked with `-ss {t} -t {duration} -i pipe:0`, feeding from byte 0:
   - FFmpeg rapidly parses the initial cached header (chunks 0..3, already in memory from probing/session creation).
   - FFmpeg fast-skips intermediate video packets without decoding (since `-c:v copy` is active).
   - Only chunks covering the range up to $t + \text{duration}$ are pulled from Telegram.
   - As soon as the segment time range is satisfied, FFmpeg closes stdout and terminates, which triggers the feeder to stop immediately.
   - Crucially: **No bytes after $t + \text{duration}$ are ever requested from Telegram.**
4. For sequential segments ($i, i+1, i+2...$), chunks are already present in `MediaChunkCache` or fetched sequentially, amortizing any startup overhead to near-zero.
5. **Fallback Safety**: If any seek fails to locate keyframes within the expected window, the feeder gracefully streams forward from the nearest cached position, guaranteeing stream continuity.

### 2.2 6-Second fMP4 Segmentation & Keyframe Alignment
**Question**: Is a 6-second segment duration reliable given video keyframe intervals (GOP)?

**Analysis & Findings**:
1. Real-world H.264 streams have GOP sizes typically between 24 and 120 frames (1.0 to 4.0 seconds at 24/30/60 fps).
2. A 6.0-second segment duration provides a clean multiple of standard keyframe intervals:
   - For 2.0s GOP: exactly 3 GOPs per segment.
   - For 3.0s GOP: exactly 2 GOPs per segment.
   - For 4.0s GOP: segments start on keyframes and align naturally.
3. Stream-copying (`-c:v copy`) avoids re-encoding artifacts and uses negligible CPU (< 1%).
4. Each segment generated with `-movflags frag_keyframe+empty_moov+default_base_moof` is an **independent, self-contained fMP4 container** containing its own `ftyp` + `moov` and `moof` + `mdat` atoms, allowing the browser MSE / HLS demuxer to decode and play it independently.

---

## 3. Component Architecture & Detailed Design

### 3.1 Segment Generation Engine (`SegmentService`)
* **Segment Duration**: Default $D = 6.0$ seconds (configurable via `HLS_SEGMENT_DURATION_SECONDS`).
* **Total Segments**: $N = \lceil \text{Duration} / D \rceil$.
* **Segment Time Window**: For segment $k \in [0, N-1]$:
  $$\text{start\_time} = k \times D, \quad \text{duration} = \min(D, \text{TotalDuration} - \text{start\_time})$$
* **FFmpeg Command**:
  ```bash
  ffmpeg -loglevel error -nostdin \
    -ss {start_time:.3f} \
    -t {duration:.3f} \
    -i pipe:0 \
    -map 0:v:0? -map 0:a:0? \
    -c:v copy \
    -c:a {copy|aac} -b:a 192k \
    -movflags frag_keyframe+empty_moov+default_base_moof \
    -f mp4 pipe:1
  ```
* **Audio Handling**:
  - Browser-native codecs (`aac`, `mp3`): `-c:a copy`.
  - Incompatible codecs (`ac3`, `eac3`, `dts`, `truehd`, `flac`, etc.): `-c:a aac -b:a 192k`.

### 3.2 Bounded Segment Cache (`BoundedSegmentCache`)
* **Capacity**: Configurable memory bound (default 64 MB per session, `SEGMENT_CACHE_MAX_MB`).
* **Eviction Policy**: Strictly Least Recently Used (LRU).
* **Concurrency Deduplication**: When multiple callers (browser request + prefetcher) request segment $k$ concurrently:
  - An `asyncio.Future` is registered under `_in_flight[k]`.
  - The initiator executes FFmpeg generation and sets the future result.
  - Concurrent callers await the existing future without duplicate FFmpeg process spawning.
* **Session Lifecycle**: When `session.close()` or `DELETE /api/media/session/{id}` is executed, the segment cache is completely cleared.

### 3.3 Adaptive Initial Prebuffer Engine (`AdaptivePrebufferEngine`)
Rather than downloading an arbitrary percentage (e.g. 10%), B10 uses B8 measurements to establish an intelligent, time-based target:
* Let $T = \text{measured download throughput in bps}$ (`ThroughputEstimator`).
* Let $R = \text{media playback bitrate in bps}$ (from probed metadata or duration).
* Let $M = \text{sustainability margin}$ (1.15x).
* **Sustainability Ratio**: $S = \frac{T}{R \times M}$.

#### Prebuffer Target Policy:
| Sustainability Ratio ($S$) | Network Headroom | Target Prebuffer Seconds | Target Segments ($D=6s$) |
| :--- | :--- | :--- | :--- |
| $S \ge 2.0$ | High Headroom (Fast DL) | **6.0s** | 1 Segment (Instant Start) |
| $1.2 \le S < 2.0$ | Good Headroom | **12.0s** | 2 Segments |
| $1.0 \le S < 1.2$ | Tight Headroom | **18.0s** | 3 Segments |
| $0.7 \le S < 1.0$ | Deficit / Drain Risk | **30.0s** | 5 Segments |
| $S < 0.7$ | Severe Bottleneck | **48.0s** | 8 Segments |

* **Prebuffer Readiness Endpoint**: `GET /api/media/session/{session_id}/prebuffer`
  - Returns `is_ready`, `buffered_segments`, `target_segments`, `buffered_seconds`, `target_seconds`, `sustainability_ratio`, `buffer_health`.

### 3.4 Background Prefetch Manager (`BackgroundPrefetchManager`)
* Continuously maintains a forward buffer ahead of the current playhead segment $p$.
* **Pacing by B8 Buffer Health**:
  - `STALLED` / `CRITICAL`: Prefetch up to 6–8 segments ahead aggressively.
  - `LOW`: Prefetch 3–4 segments ahead.
  - `HEALTHY`: If forward buffer has $\ge 30$ seconds, pause prefetching to conserve bandwidth and cache space (`PAUSE_PREFETCH`).
* **Seek Invalidation**: If playhead jumps from segment $p_1$ to $p_2$, existing prefetch tasks are canceled immediately and reassigned starting at $p_2 + 1$.

### 3.5 HLS / Browser Delivery Specification
* **HLS Master/Media Playlist**: `GET /api/media/session/{session_id}/master.m3u8`
  ```m3u8
  #EXTM3U
  #EXT-X-VERSION:3
  #EXT-X-TARGETDURATION:6
  #EXT-X-MEDIA-SEQUENCE:0
  #EXT-X-PLAYLIST-TYPE:VOD
  #EXTINF:6.000,
  segment/0.mp4
  #EXTINF:6.000,
  segment/1.mp4
  ...
  #EXT-X-ENDLIST
  ```
* **Segment Delivery**: `GET /api/media/session/{session_id}/segment/{segment_idx}.mp4`
  - Served with `Content-Type: video/mp4` and `Cache-Control: public, max-age=3600`.
  - Cache hits served in < 10ms directly from memory.

---

## 4. Seeking Workflow

```
User seeks to 00:05:00 (300 seconds)
                    │
                    ▼
Video.js calculates target segment: idx = floor(300 / 6.0) = 50
                    │
                    ▼
Browser requests: GET /api/media/session/{id}/segment/50.mp4
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
    [Cache Hit]           [Cache Miss]
Serve in < 10ms                │
                               ▼
                    BackgroundPrefetchManager cancels old worker (0..5)
                               │
                               ▼
                    SegmentService fetches & generates segment 50
                               │
                               ▼
                    Segment 50 stored in BoundedSegmentCache & served
                               │
                               ▼
                    Prefetcher resumes forward queue: 51, 52, 53...
```
* **Zero Wasted Bandwidth**: Intermediate segments (1..49) are **never downloaded**.

---

## 5. Failure Handling & Process Cleanup Guarantees

1. **FFmpeg Subprocess Lifecycle**:
   - Every FFmpeg subprocess is wrapped in `try...finally` with explicit stdin/stdout closure, `terminate()`, and timeout-backed `kill()`.
   - Guaranteed **zero orphaned FFmpeg processes** on client disconnect, seek cancel, or timeout.
2. **Telegram Slowdown / Temporary Timeout**:
   - `MediaStreamSession` handles chunk retries while serving already-cached segments from `BoundedSegmentCache`.
   - `BufferHealthEngine` transitions health state to `CRITICAL`/`STALLED`, prompting adaptive prebuffer extension.
3. **Session Expiration**:
   - `MediaSessionManager` periodically cleans up inactive sessions, releasing both raw MKV chunks (`MediaChunkCache`) and remuxed fMP4 segments (`BoundedSegmentCache`).

---

## 6. Migration & Backward Compatibility Strategy

* **B9 Progressive Playback (`/play.mp4`)**: Remains 100% active and functional.
* **B6 RFC 7233 Range Streaming (`/stream/{id}`)**: Remains 100% active and functional.
* **B10 HLS Player (`/player`)**: Serves modern Video.js with HLS segmented playback by default, while retaining a 1-click toggle to test B9 progressive mode.
