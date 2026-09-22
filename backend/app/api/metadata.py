from typing import Optional
from fastapi import APIRouter, Query

from app.models.metadata import MovieMetadata, TrendingMoviesResponse
from app.services.tmdb import tmdb_service

router = APIRouter()


@router.get("/status")
async def get_metadata_status():
    """Check if TMDb API integration is configured and available."""
    configured = tmdb_service.is_configured()
    return {
        "status": "ready" if configured else "unconfigured",
        "configured": configured,
    }


@router.get("/movie", response_model=MovieMetadata)
async def get_movie_metadata(
    title: str = Query(..., description="Movie title to look up"),
    year: Optional[int] = Query(None, description="Optional release year"),
):
    """Retrieve enriched movie metadata including posters, backdrops, ratings, synopsis, and cast."""
    return await tmdb_service.search_and_get_metadata(title=title, year=year)


@router.get("/trending", response_model=TrendingMoviesResponse)
async def get_trending_movies(
    time_window: str = Query("week", pattern="^(day|week)$", description="Trending timeframe ('day' or 'week')"),
    page: int = Query(1, ge=1, le=10, description="Page number"),
):
    """Retrieve top trending movies from TMDb for homepage discovery."""
    return await tmdb_service.get_trending_movies(time_window=time_window, page=page)


@router.get("/popular", response_model=TrendingMoviesResponse)
async def get_popular_movies(
    page: int = Query(1, ge=1, le=10, description="Page number"),
):
    """Retrieve popular movies from TMDb."""
    return await tmdb_service.get_popular_movies(page=page)


@router.get("/top-rated", response_model=TrendingMoviesResponse)
async def get_top_rated_movies(
    page: int = Query(1, ge=1, le=10, description="Page number"),
):
    """Retrieve top rated movies from TMDb."""
    return await tmdb_service.get_top_rated_movies(page=page)


@router.get("/discover", response_model=TrendingMoviesResponse)
async def discover_movies(
    language: str = Query("ml", description="Language code (e.g., 'ml', 'ta', 'hi', 'en')"),
    sort_by: str = Query("popularity.desc", description="Sort order"),
    page: int = Query(1, ge=1, le=10, description="Page number"),
):
    """Discover regional or category movies from TMDb."""
    return await tmdb_service.discover_movies(language=language, sort_by=sort_by, page=page)

