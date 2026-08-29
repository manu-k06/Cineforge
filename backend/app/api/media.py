import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.models.media import (
    B52DiagnosticReport,
    B52DualComparisonResponse,
    MediaMultiRangeBenchmarkItem,
    MediaMultiRangeBenchmarkResponse,
    MediaRangeBenchmarkResponse,
    PerformanceDiagnosticResponse,
)
from app.services import media_reader_service

router = APIRouter()


@router.get(
    "/test-media-range",
    response_model=MediaRangeBenchmarkResponse,
    summary="[Development] Benchmark Arbitrary Byte Range Retrieval from Telegram Media",
)
async def test_media_range(
    message_id: int = Query(..., description="Telegram message ID of the media file"),
    start: int = Query(0, ge=0, description="Starting byte offset"),
    end: int = Query(4194303, ge=0, description="Ending byte offset (inclusive, default 4MB - 1)"),
    chat_id: Optional[int] = Query(None, description="Optional chat ID where the message is located"),
) -> MediaRangeBenchmarkResponse:
    """Development-only endpoint: Reads an exact byte range from a Telegram media file and returns performance benchmarks."""
    try:
        reader = await media_reader_service.get_reader_for_message(
            message_id=message_id,
            chat_id=chat_id,
        )
        bench_data = await reader.benchmark_range(start=start, end=end)
        return MediaRangeBenchmarkResponse(**bench_data)
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
            detail=f"Failed during range benchmark: {str(e)}",
        )


@router.get(
    "/test-media-benchmark",
    response_model=MediaMultiRangeBenchmarkResponse,
    summary="[Development] Run Comprehensive Multi-Range & Seek Benchmarks",
)
async def test_media_benchmark(
    message_id: int = Query(..., description="Telegram message ID of the media file"),
    chat_id: Optional[int] = Query(None, description="Optional chat ID where the message is located"),
) -> MediaMultiRangeBenchmarkResponse:
    """Development-only endpoint: Runs sequential and non-zero seek range benchmarks on a Telegram media file."""
    try:
        reader = await media_reader_service.get_reader_for_message(
            message_id=message_id,
            chat_id=chat_id,
        )
        file_size = reader.get_file_size()
        file_name = reader.get_file_name()

        # Define benchmark test ranges
        r1_end = min(4 * 1024 * 1024 - 1, file_size - 1)
        r2_start = min(4 * 1024 * 1024, file_size - 1)
        r2_end = min(8 * 1024 * 1024 - 1, file_size - 1)
        r3_start = min(8 * 1024 * 1024, file_size - 1)
        r3_end = min(24 * 1024 * 1024 - 1, file_size - 1)

        if file_size > 510 * 1024 * 1024:
            seek_start = 500 * 1024 * 1024
            seek_end = min(504 * 1024 * 1024 - 1, file_size - 1)
            seek_label = "Seek Test: 500 MB - 504 MB (4 MB)"
        else:
            half = file_size // 2
            seek_start = half
            seek_end = min(half + 4 * 1024 * 1024 - 1, file_size - 1)
            seek_label = f"Seek Test: Mid-file ({round(half / (1024*1024), 1)} MB, 4 MB span)"

        test_ranges = [
            ("Initial Header & Chunk (0 - 4 MB)", 0, r1_end),
            ("Sequential Chunk (4 MB - 8 MB)", r2_start, r2_end),
            ("Sustained Range (8 MB - 24 MB, 16 MB span)", r3_start, r3_end),
            (seek_label, seek_start, seek_end),
        ]

        items = []
        total_bytes = 0
        total_time = 0.0

        for label, start, end in test_ranges:
            if start >= file_size:
                continue
            bench = await reader.benchmark_range(start=start, end=end)
            items.append(
                MediaMultiRangeBenchmarkItem(
                    range_label=label,
                    start=bench["requested_start"],
                    end=bench["requested_end"],
                    bytes_read=bench["bytes_read"],
                    elapsed_seconds=bench["elapsed_seconds"],
                    throughput_MB_per_sec=bench["throughput_MB_per_sec"],
                    throughput_mbps=bench["throughput_mbps"],
                )
            )
            total_bytes += bench["bytes_read"]
            total_time += bench["elapsed_seconds"]

        total_time_safe = max(total_time, 0.0001)
        avg_MBps = round((total_bytes / (1024 * 1024)) / total_time_safe, 2)
        avg_mbps = round((total_bytes * 8 / 1_000_000) / total_time_safe, 2)

        return MediaMultiRangeBenchmarkResponse(
            success=True,
            message_id=message_id,
            file_name=file_name,
            file_size=file_size,
            total_bytes_benchmarked=total_bytes,
            total_elapsed_seconds=round(total_time, 3),
            average_throughput_MB_per_sec=avg_MBps,
            average_throughput_mbps=avg_mbps,
            results=items,
        )

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
            detail=f"Benchmark execution failed: {str(e)}",
        )


@router.get(
    "/test-diagnostic",
    response_model=PerformanceDiagnosticResponse,
    summary="[Development] Run Deep B5.1 Media Access & Throughput Diagnostic",
)
async def test_diagnostic(
    message_id: int = Query(..., description="Telegram message ID of the media file"),
    chat_id: Optional[int] = Query(None, description="Optional chat ID where the message is located"),
) -> PerformanceDiagnosticResponse:
    """Development-only endpoint: Runs deep diagnostic profiling."""
    try:
        data = await media_reader_service.run_diagnostic(
            message_id=message_id,
            chat_id=chat_id,
        )
        return PerformanceDiagnosticResponse(**data)
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
            detail=f"Diagnostic run failed: {str(e)}",
        )


@router.get(
    "/test-b5-2-diagnostic",
    response_model=B52DualComparisonResponse,
    summary="[Development Milestone B5.2] Comprehensive Throughput & Media Bitrate Validation",
)
async def test_b5_2_diagnostic(
    message_id: int = Query(..., description="Telegram message ID of primary media file (File A)"),
    control_message_id: Optional[int] = Query(
        None, description="Optional Telegram message ID of a second control video file (File B)"
    ),
    chat_id: Optional[int] = Query(None, description="Optional chat ID for primary media file"),
    control_chat_id: Optional[int] = Query(None, description="Optional chat ID for control video file"),
) -> B52DualComparisonResponse:
    """Milestone B5.2 diagnostic: Validates DC routing, video bitrate calculation, direct Telethon vs MediaReader, and control file comparison."""
    try:
        response = await media_reader_service.compare_two_files(
            message_id_a=message_id,
            message_id_b=control_message_id,
            chat_id_a=chat_id,
            chat_id_b=control_chat_id,
        )
        return response
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
            detail=f"B5.2 diagnostic failed: {str(e)}",
        )
