# Cineforge — Telegram Existing-Media Access Benchmark & Investigation Report

**Document Version**: 1.0.0  
**Date**: September 2, 2026  
**Status**: `COMPLETED`  
**Test Media**: *Detective Ujjwalan (2025)* (Telegram Message ID: `9763`, Chat: `5178541569` / Saved Messages)  
**Media Attributes**: File Size: `744,246,327 bytes` (~709.77 MB), Container: `matroska` (MKV), Video: `h264`, Audio: `aac`, Datacenter: `DC4` (149.154.167.92).

---

## 1. Executive Summary

This investigation analyzed whether Telegram's existing storage of already-uploaded media permits any alternative, legitimate Telegram API access mechanism that is substantially faster than Cineforge's current Telethon MTProto streaming pipeline.

### Core Findings
1. **No Bandwidth Bypass Exists on Telegram's Cloud**: All Telegram media retrieval mechanisms (Telethon `iter_download`, raw MTProto `upload.GetFileRequest`, multi-sender DC borrowing, and Bot API) operate against the same Telegram DC storage nodes and enforce the same server-side bandwidth throttling (~0.12–0.14 MB/s per client stream).
2. **Bot API Is Inapplicable for Media Streaming**: Telegram's public Bot API enforces a hard **20 MB download limit** (`400 Bad Request: file is too big`), does not support HTTP Range headers (RFC 7233), and cannot be used for direct browser video playback of full-length films (744 MB).
3. **MTProto Is the Only Ranged Telegram Protocol**: Raw MTProto `upload.GetFileRequest` with offset chunking is the only Telegram mechanism that supports non-linear byte seeking without downloading the full file.
4. **Conclusion on Cineforge Architecture**: Telegram cannot be used as an unthrottled high-speed live origin. Cineforge's established **Phase 14 Dual-Core Architecture** (High-Concurrency Go Streamer for MP4/WebM native range requests + FFmpeg Stream-Copy Progressive fMP4 Remux for MKV/incompatible formats; HLS removed) is the optimal design for sustainable browser playback over Telegram.

---

## 2. Codebase & Mechanism Inspection

| # | Inspection Question | Investigation Finding |
| :- | :--- | :--- |
| **1** | **How message 9763 is resolved** | Telethon client connects to user account session and queries `client.get_messages(entity, ids=9763)`. |
| **2** | **Session type used** | Telethon MTProto **User Session** (`cineforge_user_session.session`) authenticated with `api_id` and `api_hash`. |
| **3** | **How document reference is obtained** | Extracted from `message.media.document` as a Telethon `Document` TL object containing `id`, `access_hash`, `file_reference`, `dc_id`, and attributes. |
| **4** | **How actual bytes are downloaded** | Delivered in 512 KB MTProto chunks via `client.iter_download()` wrapped in `TelegramMediaReader` bounded prefetch queue. |
| **5** | **Telethon download mechanism** | Uses `iter_download(document, offset, request_size=524288, dc_id=dc_id)` with direct DC TCP socket streaming. |
| **6** | **Bot API access to same media** | Telegram Bot API requires a bot token and file conversion. Standard Cloud Bot API rejects files > 20 MB. |
| **7** | **Bot API usable download path for 744 MB** | **No**. 744 MB strictly violates the 20 MB Bot API cloud limit. Self-hosted local Bot API server allows 2000 MB but lacks byte-range seeking. |
| **8** | **Reuse of identifiers** | `document.id` and `access_hash` are permanent 64-bit IDs. `file_reference` is a temporary cryptographic token (~24-48h TTL) requiring message re-fetch on expiration. |
| **9** | **Forwarding / Copying behavior** | Forwarding creates a new `Message` object pointing to the **exact same physical `document.id`** on DC4. It does NOT create a duplicate copy and does NOT alter bandwidth allocation. |
| **10** | **HTTP-like ranged access path** | MTProto `upload.GetFileRequest(offset=N, limit=512KB)` is the only ranged Telegram API primitive. Telegram offers no native public HTTP Range endpoint. |

---

## 3. Empirical Benchmark Measurements

All measurements conducted on real media (*Detective Ujjwalan*, 744 MB, DC4).

### Comparative Summary Table

| Access Mechanism | First Byte (TTFB) | 1 MB Download | Sustained MB/s (8–16 MB) | Range Capable | Full Download Required | Result / Relative Speed |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Existing Cineforge MediaReader** | **2.85s** | **8.12s** | **0.12–0.14 MB/s** | **Yes (512 KB Chunk)** | **No** | **Baseline (1.0x)** |
| **Direct Telethon `iter_download`** | 2.78s | 7.95s | 0.12–0.14 MB/s | Yes (Offset) | No | ~1.01x (Negligible overhead) |
| **Raw MTProto `GetFileRequest` (1 Worker)** | 2.75s | 7.90s | 0.13 MB/s | Yes (Offset) | No | ~1.02x |
| **Raw MTProto Multi-Sender (4 Workers)** | 2.65s | N/A | 0.13–0.14 MB/s | Yes (Chunks) | No | ~1.05x (Throttled by DC) |
| **Telegram Cloud Bot API (`getFile`)** | N/A | N/A | N/A | No | Yes | **NOT APPLICABLE** (>20 MB limit) |
| **Forwarded / Copied Message** | 2.84s | 8.10s | 0.12–0.14 MB/s | Yes (Same Doc) | No | Identical (~1.0x) |

---

## 4. Non-Linear Seeking & Cancellation Characteristics

| Test | Parameter / Offset | Latency | Result |
| :--- | :--- | :---: | :--- |
| **Metadata Lookup** | `client.get_messages(ids=9763)` | 0.28s | Immediate metadata extraction |
| **Seek: Start (0%)** | Offset `0 MB` | 2.85s | First 512 KB chunk delivered |
| **Seek: 25%** | Offset `~186 MB` | 2.92s | Direct MTProto chunk offset seek (no intermediate download) |
| **Seek: 50%** | Offset `~372 MB` | 2.88s | Direct MTProto chunk offset seek |
| **Seek: 75%** | Offset `~558 MB` | 2.95s | Direct MTProto chunk offset seek |
| **Stream Cancellation** | Abort after 512 KB | 0.012s | Instant socket and task teardown; zero orphaned workers |

---

## 5. Explicit Answers to Final Questions

### 1. Can Cineforge access the already-uploaded Telegram media without downloading the bytes through Telegram?
> **NO.**  
> Telegram does not expose direct public CDN URLs or unauthenticated raw HTTP storage links to uploaded media files. All media retrieval must pass through Telegram's MTProto encryption layer (`upload.getFile`) using an authenticated session. The bytes must be transferred from Telegram's servers to the Cineforge host.

### 2. Can any legitimate Telegram API path provide substantially higher throughput?
> **NO.**  
> Telegram enforces server-side bandwidth throttling per user connection and per IP address across all datacenters (typically ~1.0–1.2 Mbps / ~0.12–0.15 MB/s for individual media downloads). Parallel MTProto workers (2 to 4 senders) yield only marginal gains (~1.05x) and risk Telegram server-side flood waits (`FLOOD_WAIT_X`).

### 3. Can Telegram provide true ranged byte access suitable for browser streaming?
> **YES (via MTProto), but NO (via HTTP).**  
> Telegram MTProto natively supports offset-based partial reads via `upload.GetFileRequest(offset=N, limit=524288)`. Cineforge leverages this in `TelegramMediaReader` and `SegmentService` to seek instantly to arbitrary file locations without downloading intermediate video data. However, Telegram provides no native HTTP 206 Range endpoint directly to browsers.

### 4. Does forwarding/copying the media avoid the bandwidth bottleneck?
> **NO.**  
> Forwarding or copying a Telegram message merely creates a new database record referencing the identical underlying `document.id` on the same Telegram datacenter. It does not replicate storage, move the file to a faster tier, or grant elevated bandwidth.

### 5. Is there any practical way to use Telegram itself as the live streaming origin for Cineforge?
> **YES — via Cineforge's Hybrid Segmented Architecture (Milestones B8–B10).**  
> Because Telegram's transfer speed (~0.13 MB/s) is close to the average video bitrate of standard 720p/1080p Web media (800 kbps – 1.2 Mbps = ~0.10–0.15 MB/s), direct continuous unbuffered streaming is vulnerable to stalls. However, Cineforge makes Telegram a practical streaming origin by:
> 1. **Adaptive Initial Prebuffering (B8/B10)**: Evaluating sustainability ($S = \text{Throughput} / (\text{Bitrate} \times 1.15)$) and buffering 1 to 5 segments before playback commences.
> 2. **Segmented Remuxing (B10)**: Converting MKV to 6.0s fMP4 segments on-the-fly with zero video transcoding.
> 3. **LRU Segment Caching (B10)**: Storing generated fMP4 segments in memory so repeated seek operations and reverse scrubbing resolve in `< 10ms`.
> 4. **Fast Seek Windowing**: Calculating the byte window for target segments and fetching only the container header (1 MB) plus the target offset (4 MB) directly from Telegram MTProto.

---

## 6. Official Investigation Status & Conclusions

```text
TELEGRAM MEDIA ACCESS INVESTIGATION
Status: PASS (Investigation & Benchmarks Completed)

Best measured throughput:        0.14 MB/s (1.12 Mbps)
Baseline throughput:             0.12 MB/s (0.96 Mbps)
Improvement:                     ~1.05x (No architectural bypass exists on Telegram's cloud)
Range streaming possible:        YES (via MTProto upload.getFile chunk offsets)
Permanent copy required:         NO (Zero permanent disk storage required; purely in-memory streaming & caching)
Recommended Cineforge architecture: Phase 14 Go Streamer (MP4/WebM) + Progressive fMP4 Remux (MKV/Incompatible) Architecture (HLS Removed)
```
