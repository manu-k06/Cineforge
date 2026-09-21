from typing import List, Optional
from pydantic import BaseModel, Field


class AiQueryInterpretation(BaseModel):
    """Structured interpretation of a user's movie search query."""
    original_query: str = Field(..., description="Original raw query entered by the user")
    is_refined: bool = Field(False, description="Whether the query was refined or corrected by AI")
    canonical_title: Optional[str] = Field(None, description="Authoritative movie/series title resolved by AI")
    year: Optional[str] = Field(None, description="Release year if identified")
    search_query: str = Field(..., description="Optimized query string to send to Telegram bot / cache")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0")
    explanation: Optional[str] = Field(None, description="Brief explanation of the resolution or typo fix")
    suggested_queries: List[str] = Field(default_factory=list, description="Alternative suggested search queries")


class AiRecommendationItem(BaseModel):
    """A single movie recommendation produced by CineAI."""
    title: str = Field(..., description="Recommended movie or show title")
    year: Optional[str] = Field(None, description="Release year")
    reason: str = Field(..., description="Why this title matches the user's mood or prompt")
    search_query: str = Field(..., description="Pre-formatted search query to stream this movie")


class AiRecommendationRequest(BaseModel):
    prompt: str = Field(..., description="Mood, theme, or natural language recommendation prompt")
    count: int = Field(5, ge=1, le=10, description="Number of recommendations to generate")


class AiRecommendationResponse(BaseModel):
    prompt: str = Field(..., description="Original prompt")
    recommendations: List[AiRecommendationItem] = Field(default_factory=list)


class AiCompanionAskRequest(BaseModel):
    movie_title: str = Field(..., description="Title of the movie being watched or discussed")
    question: str = Field(..., description="User's question regarding plot, trivia, cast, or lore")


class AiCompanionAskResponse(BaseModel):
    movie_title: str
    question: str
    answer: str
