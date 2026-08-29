from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MediaRangeBenchmarkResponse(BaseModel):
    success: bool = Field(..., description="Whether the range read was successful")
    message_id: int = Field(..., description="Telegram message ID of the media file")
    file_name: Optional[str] = Field(None, description="Original filename of the media")
    mime_type: Optional[str] = Field(None, description="MIME type of the media")
    file_size: Optional[int] = Field(None, description="Total size of the media file in bytes")
    requested_start: int = Field(..., description="Start byte of the requested range")
    requested_end: int = Field(..., description="End byte of the requested range")
    bytes_read: int = Field(..., description="Exact number of bytes retrieved from Telegram")
    elapsed_seconds: float = Field(..., description="Time taken to fetch the range in seconds")
    throughput_MB_per_sec: float = Field(..., description="Data transfer throughput in Megabytes per second (MB/s)")
    throughput_mbps: float = Field(..., description="Data transfer throughput in Megabits per second (Mbps)")
    error: Optional[str] = Field(None, description="Error message if failed")


class MediaMultiRangeBenchmarkItem(BaseModel):
    range_label: str = Field(..., description="Descriptive label for this benchmark test range")
    start: int = Field(..., description="Start byte offset")
    end: int = Field(..., description="End byte offset")
    bytes_read: int = Field(..., description="Bytes retrieved")
    elapsed_seconds: float = Field(..., description="Elapsed time in seconds")
    throughput_MB_per_sec: float = Field(..., description="Throughput in MB/s")
    throughput_mbps: float = Field(..., description="Throughput in Mbps")


class MediaMultiRangeBenchmarkResponse(BaseModel):
    success: bool = Field(..., description="Whether all benchmark tests succeeded")
    message_id: int = Field(..., description="Telegram message ID")
    file_name: Optional[str] = Field(None, description="Filename")
    file_size: Optional[int] = Field(None, description="Total file size in bytes")
    total_bytes_benchmarked: int = Field(..., description="Sum of all bytes read across benchmark tests")
    total_elapsed_seconds: float = Field(..., description="Total elapsed benchmark time")
    average_throughput_MB_per_sec: float = Field(..., description="Average transfer speed in MB/s")
    average_throughput_mbps: float = Field(..., description="Average transfer speed in Mbps")
    results: List[MediaMultiRangeBenchmarkItem] = Field(default_factory=list, description="Individual range results")
    error: Optional[str] = Field(None, description="Error message if failed")


class PerformanceDiagnosticResponse(BaseModel):
    success: bool = Field(..., description="Whether the diagnostic run completed successfully")
    message_id: int = Field(..., description="Message ID tested")
    file_name: str = Field(..., description="Media filename")
    file_size_bytes: int = Field(..., description="Total file size in bytes")
    document_dc_id: int = Field(..., description="Telegram Media Datacenter ID")
    connection_reused: bool = Field(True, description="Whether persistent client connection was reused")
    effective_chunk_size_bytes: int = Field(..., description="MTProto chunk request size")
    single_chunk_latency_seconds: float = Field(..., description="Single 512KB chunk round-trip time")
    single_chunk_throughput_MB_per_sec: float = Field(..., description="Single chunk transfer speed in MB/s")
    different_range_sizes: List[MediaMultiRangeBenchmarkItem] = Field(
        default_factory=list, description="Benchmarks for 1MB, 4MB, 8MB, 16MB, 32MB"
    )
    repeated_sequential_reads: List[MediaMultiRangeBenchmarkItem] = Field(
        default_factory=list, description="Benchmarks for adjacent ranges: 0-4MB, 4-8MB, 8-12MB, 12-16MB"
    )
    parallel_vs_sequential: Dict[str, Any] = Field(
        default_factory=dict, description="Comparison between 1x4MB sequential vs 4x1MB parallel workers"
    )
    analysis_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Identified bottleneck, memory usage, and recommended configuration"
    )
    error: Optional[str] = Field(None, description="Error if diagnostic failed")


class MediaBitrateInfo(BaseModel):
    duration_seconds: Optional[int] = Field(None, description="Video duration in seconds if present in attributes")
    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")
    supports_streaming: Optional[bool] = Field(None, description="Whether fast streaming flag is enabled")
    video_codec: Optional[str] = Field(None, description="Video codec")
    audio_codec: Optional[str] = Field(None, description="Audio codec")
    calculated_bitrate_mbps: Optional[float] = Field(None, description="Bitrate calculated from duration and size")
    bitrate_status: str = Field(..., description="Human readable explanation of bitrate calculation or unavailability")


class DirectTelethonComparison(BaseModel):
    cineforge_media_reader_4mb_seconds: float = Field(..., description="Time taken by CineForge MediaReader (s)")
    cineforge_media_reader_4mb_MBps: float = Field(..., description="Speed via CineForge MediaReader (MB/s)")
    cineforge_media_reader_4mb_mbps: float = Field(..., description="Speed via CineForge MediaReader (Mbps)")
    direct_telethon_iter_download_4mb_seconds: float = Field(..., description="Time taken by raw Telethon iter_download (s)")
    direct_telethon_iter_download_4mb_MBps: float = Field(..., description="Speed via raw Telethon iter_download (MB/s)")
    direct_telethon_iter_download_4mb_mbps: float = Field(..., description="Speed via raw Telethon iter_download (Mbps)")
    overhead_difference_percent: float = Field(..., description="Percentage overhead of MediaReader vs raw Telethon")
    conclusion: str = Field(..., description="Assessment of whether MediaReader introduces overhead")


class ParallelWorkerItem(BaseModel):
    workers: int = Field(..., description="Number of parallel DC senders/workers")
    bytes_read: int = Field(..., description="Bytes read")
    elapsed_seconds: float = Field(..., description="Elapsed time (s)")
    throughput_MB_per_sec: float = Field(..., description="Speed (MB/s)")
    throughput_mbps: float = Field(..., description="Speed (Mbps)")


class ParallelWorkersTest(BaseModel):
    results: List[ParallelWorkerItem] = Field(default_factory=list, description="Results for 1, 2, and 4 workers")
    speedup_1_to_4: float = Field(..., description="Speedup ratio from 1 worker to 4 workers")
    parallelism_viable: bool = Field(..., description="Whether parallelism provides significant speedup")


class B52DiagnosticReport(BaseModel):
    success: bool = Field(..., description="Whether the diagnostic run completed successfully")
    message_id: int = Field(..., description="Tested Telegram message ID")
    file_name: str = Field(..., description="Media filename")
    file_size_bytes: int = Field(..., description="Total size in bytes")
    file_size_mb: float = Field(..., description="Total size in MB")
    mime_type: str = Field(..., description="MIME type")
    dc_info: Dict[str, Any] = Field(default_factory=dict, description="Telegram Datacenter and connection info")
    media_bitrate_info: MediaBitrateInfo = Field(..., description="Extracted video attributes and bitrate")
    range_size_benchmarks: List[MediaMultiRangeBenchmarkItem] = Field(
        default_factory=list, description="Range reads for 1MB, 4MB, 8MB, 16MB"
    )
    direct_telethon_comparison: DirectTelethonComparison = Field(
        ..., description="Comparison between Cineforge MediaReader and direct raw Telethon iter_download"
    )
    parallel_workers_test: ParallelWorkersTest = Field(
        ..., description="Controlled 1, 2, and 4 worker parallel test results"
    )
    analysis_answers: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed answers to the 7 core questions"
    )
    error: Optional[str] = Field(None, description="Error if failed")


class B52DualComparisonResponse(BaseModel):
    success: bool = Field(..., description="Whether comparison completed")
    file_a: B52DiagnosticReport = Field(..., description="Diagnostic report for File A (Test Movie)")
    file_b: Optional[B52DiagnosticReport] = Field(None, description="Diagnostic report for File B (Control Video)")
    is_bottleneck_media_specific: bool = Field(..., description="Whether throughput differs significantly between files")
    summary: str = Field(..., description="High-level summary of findings")
