from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class BufferHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    LOW = "LOW"
    CRITICAL = "CRITICAL"
    STALLED = "STALLED"


class PrefetchAction(str, Enum):
    AGGRESSIVE_PREFETCH = "aggressive_prefetch"
    NORMAL_PREFETCH = "normal_prefetch"
    PAUSE_PREFETCH = "pause_prefetch"
    STALL_WARNING = "stall_warning"


class SessionBufferingMetrics(BaseModel):
    session_id: str = Field(..., description="Active streaming session ID")
    downloaded_bytes: int = Field(..., description="Total raw bytes downloaded from Telegram MTProto for this session")
    buffered_bytes: int = Field(..., description="Total active bytes currently retained in session LRU cache")
    buffered_seconds: Optional[float] = Field(None, description="Estimated playback time in seconds held in buffer")
    download_throughput_bps: Optional[int] = Field(
        None, description="Estimated download throughput in bits/sec based on recent chunk downloads"
    )
    playback_bitrate_bps: Optional[int] = Field(
        None, description="Actual media bitrate in bits/sec from probe metadata or file duration"
    )
    playback_drain_rate_bps: Optional[int] = Field(
        None, description="Rate at which media playback consumes buffer (bits/sec)"
    )
    net_buffer_growth_rate_bps: Optional[int] = Field(
        None, description="Net buffer fill rate in bps (download throughput - drain rate)"
    )
    buffer_health: BufferHealthState = Field(
        ..., description="Current buffer health state: HEALTHY, LOW, CRITICAL, or STALLED"
    )
    time_to_stall_seconds: Optional[float] = Field(
        None, description="Estimated seconds until playback stalls if net growth rate is negative"
    )
    sustainable: Optional[bool] = Field(
        None, description="Whether current download rate can sustain continuous playback with safety margin"
    )
    prefetch_recommended: bool = Field(
        ..., description="Whether adaptive prefetching should actively fetch chunks ahead"
    )
    prefetch_action: PrefetchAction = Field(
        ..., description="Action recommendation: aggressive_prefetch, normal_prefetch, pause_prefetch, stall_warning"
    )
    recommended_prefetch_chunks: int = Field(
        ..., description="Number of chunks recommended to prefetch ahead (0 to 4)"
    )
