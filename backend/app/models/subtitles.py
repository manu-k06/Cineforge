from typing import List, Optional
from pydantic import BaseModel, Field


class SubtitleTrack(BaseModel):
    id: str = Field(..., description="Unique track identifier (e.g. 'sub_en_0', 'sub_es_1')")
    type: str = Field("external", description="Subtitle source type: 'external' or 'sync'")
    language: str = Field("en", description="ISO 639-1 language code (e.g. 'en', 'es', 'fr', 'hi')")
    label: str = Field(..., description="Clean human-readable display label: 'English', 'Spanish', etc.")
    provider: Optional[str] = Field("api", description="Subtitle provider source: 'opensubtitles', 'yify', 'sync'")
    is_default: bool = Field(False, description="Whether this track is marked as default")
    vtt_url: str = Field(..., description="Endpoint URL returning standard WebVTT subtitle stream")


class SubtitleTrackListResponse(BaseModel):
    title: Optional[str] = Field(None, description="Media title")
    year: Optional[int] = Field(None, description="Release year")
    imdb_id: Optional[str] = Field(None, description="IMDb identifier")
    stream_url: Optional[str] = Field(None, description="Optional target media stream URL for compatibility")
    tracks: List[SubtitleTrack] = Field(default_factory=list, description="Available clean subtitle tracks")
