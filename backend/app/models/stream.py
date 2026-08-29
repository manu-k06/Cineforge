from typing import Optional
from pydantic import BaseModel, Field


class CreateMediaSessionRequest(BaseModel):
    message_id: int = Field(..., description="Telegram message ID of the media file")
    chat_id: Optional[int] = Field(None, description="Optional chat or bot ID")


class CreateMediaSessionResponse(BaseModel):
    session_id: str = Field(..., description="Opaque unique streaming session ID")
    file_name: str = Field(..., description="Filename of the media")
    mime_type: str = Field(..., description="MIME type of the media (e.g. video/x-matroska or video/mp4)")
    size: int = Field(..., description="Total size in bytes")
    stream_url: str = Field(..., description="HTTP streaming endpoint URL for this session")


class MediaSessionMetrics(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    file_name: str = Field(..., description="Filename")
    file_size_bytes: int = Field(..., description="Total file size in bytes")
    cached_chunks_count: int = Field(..., description="Number of 512KB chunks currently in LRU memory cache")
    cached_bytes: int = Field(..., description="Memory currently used by cache in bytes")
    max_buffer_bytes: int = Field(..., description="Configured upper bound for cache in bytes")
    cache_hits: int = Field(..., description="Total number of chunk cache hits")
    cache_misses: int = Field(..., description="Total number of chunk cache misses")
    cache_hit_ratio: float = Field(..., description="Cache hit percentage ratio (0.0 to 1.0)")
    total_bytes_served: int = Field(..., description="Cumulative bytes served via HTTP range requests")
    last_requested_range: Optional[str] = Field(None, description="Last requested byte range string")
    created_at: float = Field(..., description="Timestamp when session was created")
    last_accessed_at: float = Field(..., description="Timestamp of most recent request")


class StreamRangeBenchmarkResponse(BaseModel):
    success: bool = Field(..., description="Whether test was successful")
    session_id: str = Field(..., description="Active session ID")
    requested_start: int = Field(..., description="Requested start byte")
    requested_end: int = Field(..., description="Requested end byte")
    bytes_served: int = Field(..., description="Bytes served")
    cache_hit: bool = Field(..., description="Whether range was satisfied from LRU cache")
    first_byte_latency_seconds: float = Field(..., description="Time to first byte in seconds")
    total_elapsed_seconds: float = Field(..., description="Total time to stream range in seconds")
    throughput_MB_per_sec: float = Field(..., description="Throughput in MB/s")
    throughput_mbps: float = Field(..., description="Throughput in Mbps")
