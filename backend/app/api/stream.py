import asyncio
import logging
import re
import time
from typing import Any, Dict, Optional, Union

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse

from app.config import settings
from app.models.buffering import SessionBufferingMetrics
from app.models.probe import SessionMetadataResponse, SubtitleTrackInfo
from app.models.stream import (
    CreateMediaSessionRequest,
    CreateMediaSessionResponse,
    MediaSessionMetrics,
    PlaybackSessionDetailResponse,
    StreamerHealthResponse,
    StreamRangeBenchmarkResponse,
)
from app.services import (
    media_probe_service,
    media_reader_service,
    remux_service,
    session_manager,
    subtitle_service,
)
from app.services.stream_session import PlaybackSession

logger = logging.getLogger("cineforge.api.stream")
router = APIRouter()

# Robust pattern supporting optional whitespace around '=' and '-'
RANGE_HEADER_PATTERN = re.compile(r"bytes\s*=\s*(\d*)\s*-\s*(\d*)", re.IGNORECASE)


@router.get(
    "/streamer/health",
    response_model=StreamerHealthResponse,
    summary="Check Go Streamer Connectivity & Health",
)
async def check_streamer_health() -> StreamerHealthResponse:
    """Verifies whether the Go streamer daemon is reachable on its configured URL."""
    streamer_url = settings.STREAMER_BASE_URL.rstrip("/")
    health_url = f"{streamer_url}/health"

    try:
        async with httpx.AsyncClient(timeout=settings.STREAMER_TIMEOUT_SECONDS) as client:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                details = resp.json()
                return StreamerHealthResponse(
                    status="healthy",
                    streamer_url=streamer_url,
                    reachable=True,
                    details=details,
                )
            else:
                return StreamerHealthResponse(
                    status="unhealthy",
                    streamer_url=streamer_url,
                    reachable=False,
                    error=f"Streamer returned HTTP {resp.status_code}",
                )
    except Exception as err:
        return StreamerHealthResponse(
            status="unreachable",
            streamer_url=streamer_url,
            reachable=False,
            error=str(err),
        )


@router.post(
    "/session",
    response_model=CreateMediaSessionResponse,
    summary="Create an Active HTTP Streaming Session for Telegram Media",
)
async def create_media_session(
    body: CreateMediaSessionRequest,
) -> CreateMediaSessionResponse:
    """Creates a lightweight playback session delegating media streaming to Go streamer."""
    if not body.message_id or body.message_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid positive message_id is required.",
        )

    chat_id = body.chat_id if body.chat_id is not None else "me"

    try:
        session = await session_manager.create_playback_session(
            chat_id=chat_id,
            message_id=body.message_id,
        )
        return CreateMediaSessionResponse(
            session_id=session.session_id,
            chat_id=session.chat_id,
            message_id=session.message_id,
            stream_url=session.stream_url,
            created_at=session.created_at,
            expires_at=session.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create streaming session: {str(e)}",
        )


@router.get(
    "/session/{session_id}",
    response_model=Union[PlaybackSessionDetailResponse, MediaSessionMetrics],
    summary="Get Playback Session Details or Real-Time Metrics",
)
async def get_session_metrics(session_id: str):
    """Returns details for a PlaybackSession or real-time cache metrics for a legacy session."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired.",
        )

    if isinstance(session, PlaybackSession) or hasattr(session, "stream_url"):
        return PlaybackSessionDetailResponse(
            session_id=session.session_id,
            chat_id=session.chat_id,
            message_id=session.message_id,
            stream_url=session.stream_url,
            created_at=session.created_at,
            expires_at=session.expires_at,
            is_expired=session.is_expired(),
        )

    return session.get_metrics()


@router.get(
    "/session/{session_id}/metadata",
    response_model=SessionMetadataResponse,
    summary="[Milestone B7] Get Probed Media Metadata, Browser Compatibility & Playback Sustainability",
)
async def get_session_metadata(session_id: str) -> SessionMetadataResponse:
    """Returns probed container/codecs, HTML5 browser compatibility, sustainability ratio, and buffer strategy."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    try:
        return await media_probe_service.get_session_metadata(session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to probe media session metadata: {str(e)}",
        )


@router.get(
    "/session/{session_id}/buffering",
    response_model=SessionBufferingMetrics,
    summary="[Milestone B8] Get Real-Time Buffer Health, Drain Rate & Playback Viability",
)
async def get_session_buffering_metrics(session_id: str) -> SessionBufferingMetrics:
    """Returns real-time buffer health, drain rate, time-to-stall, and adaptive prefetch decisions."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    return session.get_buffering_metrics()


@router.delete(
    "/session/{session_id}",
    summary="Explicitly Close Streaming Session and Free Memory",
)
async def delete_session(session_id: str):
    """Explicitly terminates session and purges its LRU memory cache."""
    clean_id = session_id.strip()
    removed = await session_manager.remove_session(clean_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{clean_id}' not found.",
        )
    return {"success": True, "message": f"Session '{clean_id}' destroyed and cache evicted."}


@router.get(
    "/stream/{session_id}",
    summary="HTTP Range Streaming Endpoint for Video Players",
)
async def stream_media(
    session_id: str,
    range_header: Optional[str] = Header(None, alias="Range"),
    raw: Optional[bool] = Query(False),
):
    """Streams video media content supporting RFC 7233 HTTP Range requests (206 Partial Content)."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    if hasattr(session, "is_expired") and session.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Streaming session '{clean_id}' has expired.",
        )

    # For PlaybackSessions (which use the Python MTProto streamer), never redirect to
    # the Go streamer — it is unreliable / may not be running. Serve bytes directly.
    # For legacy MediaStreamSessions with no Range header, fall through to direct serve.

    # If session has no metadata populated yet, resolve it dynamically via reader
    if not getattr(session, "file_size", 0) or session.file_size <= 0:
        if hasattr(session, "get_reader"):
            try:
                reader = await session.get_reader()
                if reader and reader.file_size > 0:
                    session.file_size = reader.file_size
                    session.mime_type = reader.mime_type
                    session.file_name = reader.file_name
            except Exception as meta_err:
                logger.warning("Failed to resolve reader metadata for session %s: %s", clean_id[:8], str(meta_err))

    file_size = session.file_size
    mime_type = session.mime_type

    # 1. Parse Range Header
    if range_header:
        match = RANGE_HEADER_PATTERN.match(range_header.strip())
        if not match:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail=f"Invalid Range header format: '{range_header}'. Expected 'bytes=start-end'.",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        raw_start, raw_end = match.groups()

        if raw_start == "" and raw_end == "":
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Empty byte range requested.",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        elif raw_start == "":
            # Suffix range: bytes=-500000 (last 500,000 bytes)
            suffix_len = int(raw_end)
            start = max(0, file_size - suffix_len)
            end = file_size - 1
        elif raw_end == "":
            # Open-ended range: bytes=N- (from N to EOF).
            # TG-FileStreamBot architecture: stream continuously to EOF without artificial caps.
            start = int(raw_start)
            end = file_size - 1
        else:
            # Explicit range: bytes=0-1048575
            start = int(raw_start)
            end = int(raw_end)

        # Validate range boundary bounds
        if start < 0 or start >= file_size or start > end:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail=f"Requested range ({start}-{end}) is not satisfiable for file size ({file_size}).",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        end = min(end, file_size - 1)
        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": mime_type,
            "Content-Disposition": f'inline; filename="{session.file_name}"',
            "Cache-Control": "no-cache",
        }
        status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        # No Range header: full file stream
        start = 0
        end = file_size - 1
        content_length = file_size
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": mime_type,
            "Content-Disposition": f'inline; filename="{session.file_name}"',
            "Cache-Control": "no-cache",
        }
        status_code = status.HTTP_200_OK

    return StreamingResponse(
        session.stream_byte_range(start, end),
        status_code=status_code,
        headers=headers,
        media_type=mime_type,
    )


@router.get(
    "/benchmark-stream/{session_id}",
    response_model=StreamRangeBenchmarkResponse,
    summary="[Development] Benchmark Stream Range Response Time and Cache Hits",
)
async def benchmark_stream_range(
    session_id: str,
    start: int = Query(0, ge=0, description="Start byte"),
    end: int = Query(4194303, ge=0, description="End byte (default 4MB - 1)"),
) -> StreamRangeBenchmarkResponse:
    """Measures first-byte latency, total time, throughput, and cache-hit behavior on a streaming session."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    file_size = session.file_size
    if start >= file_size or start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid range coordinates: start={start}, end={end}, file_size={file_size}.",
        )

    end = min(end, file_size - 1)
    first_chunk_idx = start // session.chunk_size
    is_cache_hit = session.cache.has(first_chunk_idx)

    t0 = time.perf_counter()
    first_byte_time = None
    bytes_read = 0

    async for chunk in session.stream_byte_range(start, end):
        if first_byte_time is None:
            first_byte_time = time.perf_counter() - t0
        bytes_read += len(chunk)

    total_time = max(time.perf_counter() - t0, 0.0001)
    fb_latency = round(first_byte_time or total_time, 3)

    mbps = round((bytes_read * 8 / 1_000_000) / total_time, 2)
    MBps = round((bytes_read / (1024 * 1024)) / total_time, 2)

    return StreamRangeBenchmarkResponse(
        success=True,
        session_id=clean_id,
        requested_start=start,
        requested_end=end,
        bytes_served=bytes_read,
        cache_hit=is_cache_hit,
        first_byte_latency_seconds=fb_latency,
        total_elapsed_seconds=round(total_time, 3),
        throughput_MB_per_sec=MBps,
        throughput_mbps=mbps,
    )


@router.get(
    "/session/{session_id}/play.mp4",
    summary="[Phase 14] Progressive Fragmented MP4 Browser Playback Stream",
)
async def play_media_fmp4(
    session_id: str,
    t: float = Query(0.0, ge=0.0, description="Seek position in seconds"),
    audio_track: int = Query(0, ge=0, description="Audio track index (default 0)"),
):
    """Streams progressive fragmented MP4 (fMP4) remuxed on-the-fly from Telegram MKV media with zero video transcoding."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    raw_name = getattr(session, "file_name", f"media_{clean_id[:8]}")
    clean_file_name = raw_name.rsplit('.', 1)[0] if '.' in raw_name else raw_name

    headers = {
        "Content-Type": "video/mp4",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Accept-Ranges": "none",
        "Content-Disposition": f'inline; filename="{clean_file_name}.mp4"',
    }

    return StreamingResponse(
        remux_service.stream_fmp4(session=session, seek_seconds=t, audio_track_idx=audio_track),
        status_code=status.HTTP_200_OK,
        headers=headers,
        media_type="video/mp4",
    )


@router.get(
    "/session/{session_id}/subtitles",
    response_model=list[SubtitleTrackInfo],
    summary="Get Available Subtitle Tracks for a Streaming Session",
)
async def get_session_subtitles(session_id: str) -> list[SubtitleTrackInfo]:
    """Discovers and returns all embedded subtitle tracks in the media session."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired.",
        )
    return await subtitle_service.get_subtitle_tracks(session)


@router.get(
    "/session/{session_id}/subtitles/{track_id}.vtt",
    response_class=Response,
    summary="Extract & Stream WebVTT Subtitle Track on Demand",
)
async def get_session_subtitle_vtt(session_id: str, track_id: int):
    """Extracts on-demand an embedded subtitle track into standard WebVTT text."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired.",
        )

    vtt_content = await subtitle_service.extract_vtt(session, track_id)
    return Response(
        content=vtt_content,
        media_type="text/vtt; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/session/{session_id}/player",
    response_class=HTMLResponse,
    summary="[Phase 14] Video.js Player & Telemetry UI",
)
async def get_player_page(session_id: str):
    """Renders modern Video.js 8+ player with Phase 11/12 Go Streamer integration and live telemetry."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

    # Safe attribute extraction for PlaybackSession vs legacy MediaStreamSession
    if hasattr(session, "file_name") and session.file_name:
        file_name = session.file_name
    elif hasattr(session, "message_id"):
        file_name = f"Telegram Document (msg {session.message_id})"
    else:
        file_name = f"Telegram Media ({clean_id[:8]})"

    if hasattr(session, "file_size") and session.file_size:
        file_size_mb = round(session.file_size / (1024 * 1024), 1)
    else:
        file_size_mb = "709.8"

    mime_type = getattr(session, "mime_type", "video/x-matroska")
    from app.services.compatibility import compatibility_service
    compat = compatibility_service.get_media_compatibility(
        filename=file_name,
        mime_type=mime_type,
    )

    is_browser_playable = compat.browser_playable
    container = compat.container or ("mp4" if is_browser_playable else "mkv")

    direct_stream_url = getattr(session, "stream_url", "")
    redirect_stream_url = f"/api/media/stream/{clean_id}"
    fmp4_stream_url = f"/api/media/session/{clean_id}/play.mp4"

    # Strict Phase 14 Playback Routing:
    # 1. Native browser containers (MP4, WebM): Stream directly via Go streamer redirect
    # 2. Incompatible containers (MKV, AVI, etc.): NEVER feed raw container to Video.js!
    #    Route automatically to FFmpeg progressive fMP4 remux endpoint (-c:v copy -c:a copy).
    if is_browser_playable:
        initial_source = redirect_stream_url
        initial_type = "video/webm" if container == "webm" else "video/mp4"
        route_badge = "NATIVE BROWSER STREAM"
        route_desc = f"Direct Go streamer playback ({container.upper()})"
    else:
        initial_source = fmp4_stream_url
        initial_type = "video/mp4"
        route_badge = "PROGRESSIVE fMP4 REMUX"
        route_desc = f"Automatic stream-copy remux ({container.upper()} → fMP4)"

    # Discover embedded subtitle tracks
    subtitle_tracks = []
    try:
        subtitle_tracks = await subtitle_service.get_subtitle_tracks(session)
    except Exception as e:
        logger.warning("Failed to discover subtitle tracks for session %s: %s", clean_id[:8], e)

    track_tags = []
    for idx, tr in enumerate(subtitle_tracks):
        if tr.is_text:
            track_tags.append(
                f'<track kind="subtitles" src="{tr.vtt_url}" srclang="{tr.language or "und"}" label="{tr.title}">'
            )
    tracks_html = "\n                ".join(track_tags)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cineforge Video Player — {file_name}</title>
    <!-- Video.js 8+ CSS -->
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        :root {{
            --bg-primary: #0a0e17;
            --bg-card: rgba(18, 26, 43, 0.85);
            --border-card: rgba(255, 255, 255, 0.08);
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }}
        body {{
            background: radial-gradient(circle at top right, #111827, #030712);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            width: 100%;
            max-width: 1200px;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-card);
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .file-info {{
            font-size: 0.9rem;
            color: var(--text-muted);
            text-align: right;
        }}
        .player-wrapper {{
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border-card);
            margin-bottom: 20px;
        }}
        .video-js {{
            width: 100%;
            aspect-ratio: 16 / 9;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 16px;
            backdrop-filter: blur(8px);
        }}
        .card-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 1.5rem;
            font-weight: 700;
            display: flex;
            align-items: baseline;
            gap: 6px;
        }}
        .card-sub {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-healthy, .badge-ready {{
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }}
        .badge-warning, .badge-low {{
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}
        .badge-critical, .badge-error {{
            background: rgba(244, 63, 94, 0.2);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.4);
        }}
        .controls-card {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-card);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .btn:hover {{
            background: rgba(255, 255, 255, 0.16);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .btn-active {{
            background: var(--accent-cyan);
            border-color: var(--accent-cyan);
            color: #042f2e;
            font-weight: 700;
        }}
        .btn-seek {{
            background: rgba(59, 130, 246, 0.2);
            border-color: rgba(59, 130, 246, 0.4);
            color: #60a5fa;
        }}
        .btn-seek:hover {{
            background: rgba(59, 130, 246, 0.35);
        }}
        .event-log-box {{
            background: #000;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 12px;
            height: 160px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.8rem;
            color: #a7f3d0;
            line-height: 1.4;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                🎬 Cineforge Video Player
            </div>
            <div class="file-info">
                Media: <span>{file_name}</span> ({file_size_mb} MB)<br>
                Session: <code style="color: #60a5fa;">{clean_id[:8]}...</code>
            </div>
        </header>

        <div class="player-wrapper">
            <video
                id="cineforge-player"
                class="video-js vjs-big-play-centered"
                controls
                preload="auto"
                data-setup='{{"fluid": true}}'
            >
                <source id="video-source" src="{initial_source}" type="{initial_type}" />
                {tracks_html}
                <p class="vjs-no-js">
                    To view this video please enable JavaScript, and consider upgrading to a web browser that supports HTML5 video.
                </p>
            </video>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-title">Playback State</div>
                <div class="card-value">
                    <span id="player-state-badge" class="badge badge-ready">READY</span>
                </div>
                <div class="card-sub" id="time-display">Time: 0.0s / --s</div>
            </div>

            <div class="card">
                <div class="card-title">ReadyState / NetworkState</div>
                <div class="card-value" id="ready-state-text" style="font-size: 1.1rem;">
                    HAVE_NOTHING (0)
                </div>
                <div class="card-sub" id="network-state-text">NETWORK_EMPTY (0)</div>
            </div>

            <div class="card">
                <div class="card-title">Seek & Latency Diagnostics</div>
                <div class="card-value" id="seek-status-text" style="font-size: 1.1rem;">
                    Ready
                </div>
                <div class="card-sub" id="seek-latency-text">Last seek latency: --ms</div>
            </div>

            <div class="card">
                <div class="card-title">Error / Compatibility</div>
                <div class="card-value" id="error-status-text" style="font-size: 1.1rem; color: #34d399;">
                    None
                </div>
                <div class="card-sub" id="error-detail-text">No playback errors</div>
            </div>
        </div>

        <div class="card controls-card">
            <div style="font-size: 0.9rem; color: var(--text-muted);">
                Interactive Seek Controls:
            </div>
            <div style="display: flex; gap: 8px;">
                <button id="btn-seek-25" class="btn btn-seek" onclick="seekPercent(0.25)">Seek 25% (1840s)</button>
                <button id="btn-seek-50" class="btn btn-seek" onclick="seekPercent(0.50)">Seek 50% (3680s)</button>
                <button id="btn-seek-75" class="btn btn-seek" onclick="seekPercent(0.75)">Seek 75% (5520s)</button>
            </div>
        </div>

        <div class="card controls-card" style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 600;">Subtitles:</span>
                <input type="file" id="sub-file-input" accept=".srt,.vtt" style="display: none;" onchange="handleSubFileSelect(event)" />
                <button class="btn btn-seek" onclick="document.getElementById('sub-file-input').click()" style="display: inline-flex; align-items: center; gap: 6px;">
                    📂 Load Subtitle (.srt / .vtt)
                </button>
                <span id="sub-active-badge" class="badge badge-ready" style="display: none;">Custom Loaded</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 0.85rem; color: var(--text-muted);">Sync Offset:</span>
                <button class="btn btn-seek" onclick="adjustSubOffset(-0.5)" title="Shift subtitles 0.5s earlier">-0.5s</button>
                <span id="sub-offset-val" style="font-family: monospace; font-size: 0.9rem; min-width: 45px; text-align: center;">0.0s</span>
                <button class="btn btn-seek" onclick="adjustSubOffset(0.5)" title="Shift subtitles 0.5s later">+0.5s</button>
                <button class="btn btn-seek" onclick="resetSubOffset()" style="padding: 6px 8px; font-size: 0.75rem;">Reset</button>
            </div>
        </div>

        <div class="card controls-card">
            <div style="font-size: 0.9rem; color: var(--text-muted); display: flex; align-items: center; gap: 10px;">
                <span style="text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.05em; font-weight: 600;">Routing:</span>
                <span class="badge badge-ready">{route_badge}</span>
                <span>{route_desc}</span>
            </div>
            <div>
                <a id="btn-open-vlc" class="btn" style="background: #ea580c; color: white; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;" href="{direct_stream_url}" target="_blank">▶ Open in VLC / External Player</a>
            </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <div class="card-title" style="display: flex; justify-content: space-between;">
                <span>Live Player Event Log & Network Range Probing</span>
                <span id="event-count-text">0 events</span>
            </div>
            <div id="event-log-container" class="event-log-box"></div>
        </div>
    </div>

    <!-- Video.js 8+ Script -->
    <script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
    <script>
        const sessionId = "{clean_id}";
        const directGoUrl = "{direct_stream_url}";
        const redirectUrl = "{redirect_stream_url}";

        // Global diagnostic structures for automated inspection
        window.__playerEvents = [];
        window.__seekTimestamps = [];
        window.__rangeRequests = [];
        window.__lastError = null;

        function logEvent(name, detail = '') {{
            const now = performance.now();
            const timeStr = new Date().toISOString().split('T')[1].slice(0, 12);
            const entry = {{
                event: name,
                timeMs: Math.round(now),
                detail: detail,
                currentTime: player ? player.currentTime() : 0,
                readyState: player ? player.readyState() : 0,
                networkState: player ? player.networkState() : 0
            }};
            window.__playerEvents.push(entry);

            const container = document.getElementById('event-log-container');
            if (container) {{
                const line = document.createElement('div');
                line.textContent = `[${{timeStr}}] ${{name.padEnd(16)}} | ReadyState=${{entry.readyState}} NetState=${{entry.networkState}} | CurTime=${{entry.currentTime.toFixed(1)}}s ${{detail}}`;
                container.appendChild(line);
                container.scrollTop = container.scrollHeight;
            }}

            const countElem = document.getElementById('event-count-text');
            if (countElem) countElem.textContent = `${{window.__playerEvents.length}} events`;
        }}

        const player = videojs('cineforge-player', {{
            controls: true,
            fluid: true,
            preload: 'auto'
        }});
        window.__player = player;

        // Player event instrumentation
        const eventsToTrack = [
            'loadstart', 'loadedmetadata', 'loadeddata', 'canplay', 'canplaythrough',
            'play', 'playing', 'pause', 'seeking', 'seeked', 'waiting', 'stalled', 'error'
        ];

        eventsToTrack.forEach(evt => {{
            player.on(evt, () => {{
                let detail = '';
                if (evt === 'error') {{
                    const err = player.error();
                    window.__lastError = err ? {{ code: err.code, message: err.message }} : null;
                    detail = err ? `CODE=${{err.code}} MSG=${{err.message}}` : 'Unknown error';
                    
                    const errBadge = document.getElementById('player-state-badge');
                    if (errBadge) {{
                        errBadge.textContent = 'ERROR';
                        errBadge.className = 'badge badge-error';
                    }}
                    const errText = document.getElementById('error-status-text');
                    if (errText) {{
                        errText.textContent = `Error Code ${{err ? err.code : '?'}}`;
                        errText.style.color = '#fb7185';
                    }}
                    const errDetail = document.getElementById('error-detail-text');
                    if (errDetail) errDetail.textContent = detail;
                }} else if (evt === 'playing') {{
                    const readyBadge = document.getElementById('player-state-badge');
                    if (readyBadge) {{
                        readyBadge.textContent = 'PLAYING';
                        readyBadge.className = 'badge badge-ready';
                    }}
                }}
                logEvent(evt, detail);
                updateUIState();
            }});
        }});

        function updateUIState() {{
            const readyNames = ['HAVE_NOTHING (0)', 'HAVE_METADATA (1)', 'HAVE_CURRENT_DATA (2)', 'HAVE_FUTURE_DATA (3)', 'HAVE_ENOUGH_DATA (4)'];
            const netNames = ['NETWORK_EMPTY (0)', 'NETWORK_IDLE (1)', 'NETWORK_LOADING (2)', 'NETWORK_NO_SOURCE (3)'];

            const rState = player.readyState();
            const nState = player.networkState();

            document.getElementById('ready-state-text').textContent = readyNames[rState] || rState;
            document.getElementById('network-state-text').textContent = netNames[nState] || nState;

            const cur = player.currentTime();
            const dur = player.duration() || 7360.5;
            document.getElementById('time-display').textContent = `Time: ${{cur.toFixed(1)}}s / ${{dur.toFixed(1)}}s`;
        }}

        let seekStartTime = 0;
        player.on('seeking', () => {{
            seekStartTime = performance.now();
            document.getElementById('seek-status-text').textContent = 'Seeking...';
        }});
        player.on('seeked', () => {{
            const elapsed = Math.round(performance.now() - seekStartTime);
            document.getElementById('seek-status-text').textContent = 'Seeked OK';
            document.getElementById('seek-latency-text').textContent = `Last seek latency: ${{elapsed}}ms`;
        }});

        window.seekPercent = function(pct) {{
            const dur = 7360.469; // Media duration ~2h 2m 40s
            const targetSec = dur * pct;
            logEvent('manual_seek', `target=${{targetSec.toFixed(1)}}s (${{pct * 100}}%)`);

            const curSrc = (player.currentSrc && player.currentSrc()) || "";
            if (curSrc.includes('/play.mp4') || curSrc.includes('t=')) {{
                seekStartTime = performance.now();
                document.getElementById('seek-status-text').textContent = 'Seeking...';
                player.src({{
                    src: `/api/media/session/{clean_id}/play.mp4?t=${{targetSec.toFixed(1)}}`,
                    type: 'video/mp4'
                }});
                player.play().then(() => {{
                    const elapsed = Math.round(performance.now() - seekStartTime);
                    document.getElementById('seek-status-text').textContent = 'Seeked OK';
                    document.getElementById('seek-latency-text').textContent = `Last seek latency: ${{elapsed}}ms`;
                }}).catch(e => logEvent('play_rejected', e.message));
            }} else {{
                player.currentTime(targetSec);
            }}
        }};

        // Performance Resource Timing tracker
        window.__getRangeRequests = function() {{
            return performance.getEntriesByType('resource')
                .filter(r => r.name.includes(':8088') || r.name.includes('/stream/'))
                .map(r => ({{
                    name: r.name,
                    duration: Math.round(r.duration),
                    transferSize: r.transferSize,
                    encodedBodySize: r.encodedBodySize
                }}));
        }};

        window.__getDiagnostics = function() {{
            return {{
                currentTime: player.currentTime(),
                duration: player.duration(),
                readyState: player.readyState(),
                networkState: player.networkState(),
                paused: player.paused(),
                error: player.error() ? {{ code: player.error().code, message: player.error().message }} : null,
                events: window.__playerEvents,
                rangeRequests: window.__getRangeRequests()
            }};
        }};

        // Periodically update UI
        setInterval(updateUIState, 1000);

        // Retain B8/B9 telemetry polling to keep compatibility
        async function updateTelemetry() {{
            try {{
                const res = await fetch(`/api/media/session/${{sessionId}}/buffering`);
                if (res.ok) {{
                    const data = await res.json();
                }}
            }} catch (e) {{}}
        }}
        // Subtitle Sync Offset & Local Subtitle Management
        let currentSubOffset = 0.0;

        function srtToVtt(srtText) {{
            let vtt = "WEBVTT\n\n" + srtText.replace(/\r\n|\r/g, '\n');
            vtt = vtt.replace(/(\\d{2}:\\d{2}:\\d{2}),(\\d{3})/g, '$1.$2');
            return vtt;
        }}

        function loadSubtitleFile(file) {{
            const reader = new FileReader();
            reader.onload = function(e) {{
                let content = e.target.result;
                if (file.name.toLowerCase().endsWith('.srt')) {{
                    content = srtToVtt(content);
                }}
                const blob = new Blob([content], {{ type: 'text/vtt' }});
                const blobUrl = URL.createObjectURL(blob);
                const trackLabel = file.name.replace(/\\.[^/.]+$/, "") + " (Local)";

                const remoteTrack = player.addRemoteTextTrack({{
                    kind: 'subtitles',
                    srclang: 'custom',
                    label: trackLabel,
                    src: blobUrl,
                    default: true
                }}, false);

                const badge = document.getElementById('sub-active-badge');
                if (badge) {{
                    badge.style.display = 'inline-block';
                    badge.textContent = `Loaded: ${{file.name.substring(0, 18)}}`;
                }}

                setTimeout(() => {{
                    const tracks = player.textTracks();
                    for (let i = 0; i < tracks.length; i++) {{
                        if (tracks[i].label === trackLabel) {{
                            tracks[i].mode = 'showing';
                        }}
                    }}
                }}, 100);

                logEvent('subtitle_loaded', file.name);
            }};
            reader.readAsText(file);
        }}

        function handleSubFileSelect(event) {{
            const file = event.target.files[0];
            if (file) {{
                loadSubtitleFile(file);
            }}
        }}

        function adjustSubOffset(delta) {{
            currentSubOffset += delta;
            const offsetDisplay = document.getElementById('sub-offset-val');
            if (offsetDisplay) {{
                offsetDisplay.textContent = (currentSubOffset >= 0 ? '+' : '') + currentSubOffset.toFixed(1) + 's';
            }}

            const tracks = player.textTracks();
            for (let i = 0; i < tracks.length; i++) {{
                const cues = tracks[i].cues;
                if (cues) {{
                    for (let j = 0; j < cues.length; j++) {{
                        cues[j].startTime += delta;
                        cues[j].endTime += delta;
                    }}
                }}
            }}
            logEvent('subtitle_sync', `${{currentSubOffset.toFixed(1)}}s`);
        }}

        function resetSubOffset() {{
            adjustSubOffset(-currentSubOffset);
        }}

        // Drag & Drop listener on player wrapper
        const wrapper = document.querySelector('.player-wrapper');
        if (wrapper) {{
            wrapper.addEventListener('dragover', (e) => {{
                e.preventDefault();
                wrapper.style.outline = '2px dashed var(--accent-cyan)';
            }});
            wrapper.addEventListener('dragleave', () => {{
                wrapper.style.outline = 'none';
            }});
            wrapper.addEventListener('drop', (e) => {{
                e.preventDefault();
                wrapper.style.outline = 'none';
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
                    const file = e.dataTransfer.files[0];
                    if (file.name.match(/\\.(srt|vtt)$/i)) {{
                        loadSubtitleFile(file);
                    }} else {{
                        alert('Please drop a .srt or .vtt subtitle file.');
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)
