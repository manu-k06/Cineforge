import re
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.models.buffering import SessionBufferingMetrics
from app.models.probe import SessionMetadataResponse
from app.models.stream import (
    CreateMediaSessionRequest,
    CreateMediaSessionResponse,
    MediaSessionMetrics,
    StreamRangeBenchmarkResponse,
)
from app.services import media_probe_service, media_reader_service, session_manager

router = APIRouter()

# Robust pattern supporting optional whitespace around '=' and '-'
RANGE_HEADER_PATTERN = re.compile(r"bytes\s*=\s*(\d*)\s*-\s*(\d*)", re.IGNORECASE)


@router.post(
    "/session",
    response_model=CreateMediaSessionResponse,
    summary="Create an Active HTTP Streaming Session for Telegram Media",
)
async def create_media_session(
    body: CreateMediaSessionRequest,
) -> CreateMediaSessionResponse:
    """Creates a memory-bounded, prefetching MediaStreamSession for the given Telegram message."""
    try:
        reader = await media_reader_service.get_reader_for_message(
            message_id=body.message_id,
            chat_id=body.chat_id,
        )
        return await session_manager.create_session(reader)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create streaming session: {str(e)}",
        )


@router.get(
    "/session/{session_id}",
    response_model=MediaSessionMetrics,
    summary="Get Real-Time Metrics & Cache Observability for a Session",
)
async def get_session_metrics(session_id: str) -> MediaSessionMetrics:
    """Returns real-time memory usage, cache hit ratio, and bytes served for the session."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired.",
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
):
    """Streams video media content supporting RFC 7233 HTTP Range requests (206 Partial Content)."""
    clean_id = session_id.strip()
    session = await session_manager.get_session(clean_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streaming session '{clean_id}' not found or expired. Please create a session first via POST /api/media/session.",
        )

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
            # Open-ended range: bytes=1000- (from 1000 to EOF)
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
    else:
        # If no Range header provided, serve initial 4 MB probe chunk
        start = 0
        end = min(4 * 1024 * 1024 - 1, file_size - 1)

    content_length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{session.file_name}"',
        "Cache-Control": "no-cache",
    }

    return StreamingResponse(
        session.stream_byte_range(start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
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
