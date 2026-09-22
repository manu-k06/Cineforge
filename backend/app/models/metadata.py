from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CastMember(BaseModel):
    name: str = Field(..., description="Actor full name")
    character: str = Field("", description="Character or role played")
    profile_path: Optional[str] = Field(None, description="TMDb profile image path")
    profile_url: Optional[str] = Field(None, description="Full CDN URL to actor photo")


class CrewMember(BaseModel):
    name: str = Field(..., description="Crew member name")
    job: str = Field(..., description="Job role (e.g. Director, Writer)")
    department: Optional[str] = Field(None, description="Department (e.g. Directing, Writing)")


class MovieMetadata(BaseModel):
    tmdb_id: Optional[int] = Field(None, description="TMDb movie ID")
    imdb_id: Optional[str] = Field(None, description="IMDb movie identifier (e.g. 'tt1375666')")
    title: str = Field(..., description="Canonical movie title")
    original_title: Optional[str] = Field(None, description="Original release title")
    overview: Optional[str] = Field(None, description="Official plot synopsis/overview")
    release_date: Optional[str] = Field(None, description="Release date (YYYY-MM-DD)")
    year: Optional[str] = Field(None, description="Release year (YYYY)")
    rating: Optional[float] = Field(None, description="IMDb / TMDb score out of 10")
    vote_count: Optional[int] = Field(None, description="Total vote count")
    runtime: Optional[int] = Field(None, description="Duration in minutes")
    genres: List[str] = Field(default_factory=list, description="Genre tags")
    poster_url: Optional[str] = Field(None, description="Full CDN URL for 500w poster image")
    backdrop_url: Optional[str] = Field(None, description="Full CDN URL for 1280w / 4K backdrop image")
    trailer_key: Optional[str] = Field(None, description="YouTube video ID for official trailer")
    directors: List[str] = Field(default_factory=list, description="List of primary directors")
    cast: List[CastMember] = Field(default_factory=list, description="Top billed cast members")
    source: str = Field("tmdb", description="Metadata provider: 'tmdb', 'cache', or 'fallback'")


class TrendingMoviesResponse(BaseModel):
    page: int = Field(1, description="Current page")
    total_pages: int = Field(1, description="Total pages available")
    results: List[MovieMetadata] = Field(default_factory=list, description="List of trending movie metadata")
