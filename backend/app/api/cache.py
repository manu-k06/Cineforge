from fastapi import APIRouter

from app.models.cache import CacheStatsResponse
from app.services.cache_service import cache_service

router = APIRouter()


@router.get("/status", response_model=CacheStatsResponse, summary="Check Supabase Cache Status & Stats")
async def get_cache_status() -> CacheStatsResponse:
    """Returns whether Supabase caching is active, along with total cached movies and AI queries."""
    stats = await cache_service.get_stats()
    return CacheStatsResponse(**stats)
