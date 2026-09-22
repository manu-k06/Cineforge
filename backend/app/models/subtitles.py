from typing import List, Optional
from pydantic import BaseModel, Field


class SubtitleTrack(BaseModel):
    id: str = Field(..., description="Unique track identifier (e.g. 'emb_0', 'ext_en_1')")
    type: str = Field("embedded", description="Subtitle source type: 'embedded' or 'external'")
    language: str = Field("en", description="ISO 639-1 language code (e.g. 'en', 'es', 'fr')")
    label: str = Field(..., description="Human-readable display label for player menu")
    codec: Optional[str] = Field(None, description="Original subtitle codec: 'subrip', 'ass', 'mov_text', 'webvtt'")
    track_index: Optional[int] = Field(None, description="Stream index within container for embedded subtitles")
    is_default: bool = Field(False, description="Whether this track is marked as default in media container")
    vtt_url: str = Field(..., description="Endpoint URL returning standard WebVTT subtitle stream")


class SubtitleTrackListResponse(BaseModel):
    stream_url: str = Field(..., description="Target media stream URL")
    title: Optional[str] = Field(None, description="Media title")
    tracks: List[SubtitleTrack] = Field(default_factory=list, description="Available subtitle tracks")
