from typing import Optional
from pydantic import BaseModel, Field


class ProbedMediaMetadata(BaseModel):
    file_name: str = Field(..., description="Original filename of the media")
    file_size_bytes: int = Field(..., description="Total file size in bytes")
    container: Optional[str] = Field(None, description="Container format (e.g. matroska, mp4, webm)")
    duration_seconds: Optional[float] = Field(None, description="Actual duration in seconds")
    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")
    frame_rate: Optional[float] = Field(None, description="Video frame rate in fps")
    video_codec: Optional[str] = Field(None, description="Primary video codec (e.g. h264, hevc, vp9)")
    audio_codec: Optional[str] = Field(None, description="Primary audio codec (e.g. aac, ac3, opus)")
    video_bitrate_bps: Optional[int] = Field(None, description="Video stream bitrate in bits per second")
    audio_bitrate_bps: Optional[int] = Field(None, description="Audio stream bitrate in bits per second")
    total_bitrate_bps: Optional[int] = Field(None, description="Total media bitrate in bits per second")
    video_stream_count: int = Field(0, description="Number of video streams")
    audio_stream_count: int = Field(0, description="Number of audio streams")
    subtitle_stream_count: int = Field(0, description="Number of subtitle streams")
    probe_status: str = Field(..., description="Status of media probing: 'success', 'unavailable', or 'failed'")
    probe_error: Optional[str] = Field(None, description="Detailed probe error if failed or unavailable")


class BrowserCompatibilityReport(BaseModel):
    browser_playback: str = Field(
        ..., description="Overall browser playback rating: 'likely_supported', 'likely_unsupported', or 'unknown'"
    )
    reason: str = Field(..., description="Human-readable assessment of container and codec browser support")
    container_supported: Optional[bool] = Field(None, description="Whether container is natively playable in HTML5 video")
    video_codec_supported: Optional[bool] = Field(None, description="Whether video codec is widely supported")
    audio_codec_supported: Optional[bool] = Field(None, description="Whether audio codec is widely supported")


class PlaybackSustainabilityReport(BaseModel):
    source_throughput_bps: Optional[int] = Field(None, description="Measured or configured Telegram source speed in bps")
    media_bitrate_bps: Optional[int] = Field(None, description="Actual total media bitrate in bps")
    sustainability_ratio: Optional[float] = Field(None, description="Ratio of source throughput to media bitrate")
    playback_sustainable: Optional[bool] = Field(None, description="Whether playback is sustainable without buffering stalls")
    margin_applied: float = Field(..., description="Safety margin multiplier applied (e.g. 1.15)")
    explanation: str = Field(..., description="Human-readable sustainability analysis")


class BufferAnalysisReport(BaseModel):
    max_buffer_bytes: int = Field(..., description="Maximum memory buffer capacity in bytes")
    buffer_capacity_seconds: Optional[float] = Field(None, description="Seconds of playback stored at max buffer capacity")
    buffer_growth_rate_bps: Optional[int] = Field(None, description="Net buffer fill rate in bps (positive=grows, negative=drains)")
    drain_warning: Optional[str] = Field(None, description="Warning if buffer will drain during continuous playback")


class SessionMetadataResponse(BaseModel):
    session_id: str = Field(..., description="Active streaming session ID")
    metadata: ProbedMediaMetadata = Field(..., description="Probed container and codec metadata")
    compatibility: BrowserCompatibilityReport = Field(..., description="HTML5 browser compatibility assessment")
    sustainability: PlaybackSustainabilityReport = Field(..., description="Upstream throughput vs bitrate sustainability analysis")
    buffer: BufferAnalysisReport = Field(..., description="Buffer capacity and growth/drain metrics")
    recommended_buffer_strategy: str = Field(
        ..., description="Recommended buffering strategy: 'realtime', 'conservative_prefetch', 'aggressive_prefetch', or 'unsustainable'"
    )
