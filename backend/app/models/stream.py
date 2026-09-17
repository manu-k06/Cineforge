from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class CreateMediaSessionRequest(BaseModel):
    message_id: int = Field(..., description="Telegram message ID of the media file")
    chat_id: Optional[Union[int, str]] = Field("me", description="Telegram chat ID, username, or 'me'")


class CreateMediaSessionResponse(BaseModel):
    session_id: str = Field(..., description="Opaque unique streaming session ID")
    chat_id: str = Field(..., description="Telegram chat target (e.g. 'me', channel ID, or username)")
    message_id: int = Field(..., description="Telegram message ID")
    stream_url: str = Field(..., description="HTTP streaming endpoint URL for this session (Go streamer or redirect)")
    created_at: float = Field(..., description="Session creation timestamp (unix epoch)")
    expires_at: float = Field(..., description="Session expiration timestamp (unix epoch)")
    file_name: Optional[str] = Field(None, description="Filename of the media (optional)")
    mime_type: Optional[str] = Field(None, description="MIME type of the media (optional)")
    size: Optional[int] = Field(None, description="Total size in bytes (optional)")


class PlaybackSessionDetailResponse(BaseModel):
    session_id: str = Field(..., description="Playback session ID")
    chat_id: str = Field(..., description="Telegram chat identifier")
    message_id: int = Field(..., description="Telegram message ID")
    stream_url: str = Field(..., description="Target stream URL")
    created_at: float = Field(..., description="Unix timestamp of session creation")
    expires_at: float = Field(..., description="Unix timestamp of session expiration")
    is_expired: bool = Field(..., description="Whether the session has expired")


class StreamerHealthResponse(BaseModel):
    status: str = Field(..., description="Health status string ('healthy', 'unreachable', etc.)")
    streamer_url: str = Field(..., description="Configured Go streamer base URL")
    reachable: bool = Field(..., description="True if Go streamer responded to /health")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed JSON response from Go streamer")
    error: Optional[str] = Field(None, description="Error message if unreachable")


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
