from typing import Optional
from pydantic import BaseModel, Field


class CachedCandidateRecord(BaseModel):
    """Database representation of a cached movie candidate in Supabase."""
    query_normalized: str = Field(..., description="Normalized search query term")
    canonical_title: str = Field(..., description="Canonical movie title")
    candidate_id: str = Field(..., description="Unique deterministic candidate identifier")
    source_bot: str = Field("Spoty_xbot", description="Providing Telegram bot username")
    source_message_id: Optional[int] = Field(None, description="Telegram message ID")
    start_payload: Optional[str] = Field(None, description="Deep link start payload")
    callback_data: Optional[str] = Field(None, description="Button callback data")
    display_text: str = Field(..., description="Raw button or result display text")
    quality: Optional[str] = Field(None, description="Quality resolution (1080P, 720P, etc.)")
    size: Optional[str] = Field(None, description="Human readable size string")
    size_bytes: Optional[int] = Field(None, description="Size in bytes")
    language: Optional[str] = Field(None, description="Audio language")
    container: Optional[str] = Field(None, description="Container format (mp4, mkv)")
    stream_url: Optional[str] = Field(None, description="Cached direct HTTP stream URL")
    watch_url: Optional[str] = Field(None, description="Cached web player watch URL")


class CacheStatsResponse(BaseModel):
    """Operational statistics for Cineforge Supabase cache."""
    status: str = Field(..., description="'ready' or 'unconfigured'")
    cache_enabled: bool = Field(..., description="Whether caching is enabled")
    cached_movies_count: int = Field(0, description="Total cached movie candidates in Supabase")
    cached_ai_queries_count: int = Field(0, description="Total cached AI query resolutions")
