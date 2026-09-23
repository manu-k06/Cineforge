import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.services.auth import get_current_user_required

logger = logging.getLogger("cineforge.history")
router = APIRouter()


class WatchProgressPayload(BaseModel):
    title: str
    clean_title: Optional[str] = None
    year: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    stream_url: str
    candidate_title: Optional[str] = None
    quality: Optional[str] = None
    progress_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    completed: Optional[bool] = False


class WatchlistPayload(BaseModel):
    title: str
    clean_title: Optional[str] = None
    year: Optional[str] = None
    rating: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    overview: Optional[str] = None
    genres: Optional[List[str]] = Field(default_factory=list)


class BulkSyncPayload(BaseModel):
    history: List[WatchProgressPayload] = Field(default_factory=list)
    watchlist: List[WatchlistPayload] = Field(default_factory=list)


def _get_supabase_client():
    if not (settings.SUPABASE_URL and settings.SUPABASE_KEY):
        return None
    try:
        from supabase import create_client
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.warning("Supabase client init error in history API: %s", str(e))
        return None


# -------------------------------------------------------------------------
# Watch History Endpoints
# -------------------------------------------------------------------------

@router.get("/history", summary="Get user watch history")
async def get_watch_history(user: Dict[str, Any] = Depends(get_current_user_required)):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "history": []}

    try:
        res = (
            client.table("user_watch_history")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(100)
            .execute()
        )
        return {"status": "ok", "history": res.data or []}
    except Exception as e:
        logger.error("Error retrieving watch history for user %s: %s", user_id, str(e))
        return {"status": "error", "message": str(e), "history": []}


@router.post("/history", summary="Upsert movie playback progress")
async def save_watch_progress(
    payload: WatchProgressPayload,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "saved": False}

    record = {
        "user_id": user_id,
        "title": payload.title,
        "clean_title": payload.clean_title or payload.title,
        "year": payload.year,
        "poster_url": payload.poster_url,
        "backdrop_url": payload.backdrop_url,
        "stream_url": payload.stream_url,
        "candidate_title": payload.candidate_title,
        "quality": payload.quality,
        "progress_seconds": payload.progress_seconds,
        "duration_seconds": payload.duration_seconds,
        "completed": payload.completed,
    }

    try:
        res = (
            client.table("user_watch_history")
            .upsert(record, on_conflict="user_id,title")
            .execute()
        )
        return {"status": "ok", "saved": True, "record": res.data}
    except Exception as e:
        logger.error("Error upserting watch progress for %s: %s", payload.title, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record watch history: {str(e)}",
        )


@router.delete("/history/{title}", summary="Remove title from watch history")
async def delete_watch_history(
    title: str,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "deleted": False}

    try:
        client.table("user_watch_history").delete().eq("user_id", user_id).eq("title", title).execute()
        return {"status": "ok", "deleted": True}
    except Exception as e:
        logger.error("Error deleting %s from history: %s", title, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete history item: {str(e)}",
        )


# -------------------------------------------------------------------------
# Watchlist Endpoints
# -------------------------------------------------------------------------

@router.get("/watchlist", summary="Get user watchlist")
async def get_watchlist(user: Dict[str, Any] = Depends(get_current_user_required)):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "watchlist": []}

    try:
        res = (
            client.table("user_watchlist")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"status": "ok", "watchlist": res.data or []}
    except Exception as e:
        logger.error("Error retrieving watchlist for user %s: %s", user_id, str(e))
        return {"status": "error", "message": str(e), "watchlist": []}


@router.post("/watchlist", summary="Add movie to watchlist")
async def add_to_watchlist(
    payload: WatchlistPayload,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "added": False}

    record = {
        "user_id": user_id,
        "title": payload.title,
        "clean_title": payload.clean_title or payload.title,
        "year": payload.year,
        "rating": payload.rating,
        "poster_url": payload.poster_url,
        "backdrop_url": payload.backdrop_url,
        "overview": payload.overview,
        "genres": payload.genres or [],
    }

    try:
        res = (
            client.table("user_watchlist")
            .upsert(record, on_conflict="user_id,title")
            .execute()
        )
        return {"status": "ok", "added": True, "record": res.data}
    except Exception as e:
        logger.error("Error adding %s to watchlist: %s", payload.title, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to watchlist: {str(e)}",
        )


@router.delete("/watchlist/{title}", summary="Remove movie from watchlist")
async def remove_from_watchlist(
    title: str,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "removed": False}

    try:
        client.table("user_watchlist").delete().eq("user_id", user_id).eq("title", title).execute()
        return {"status": "ok", "removed": True}
    except Exception as e:
        logger.error("Error deleting %s from watchlist: %s", title, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from watchlist: {str(e)}",
        )


# -------------------------------------------------------------------------
# Bulk Sync Guest to Cloud
# -------------------------------------------------------------------------

@router.post("/history/sync-guest", summary="Bulk-sync guest localStorage history and watchlist")
async def sync_guest_data(
    payload: BulkSyncPayload,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    user_id = user["id"]
    client = _get_supabase_client()
    if not client:
        return {"status": "unconfigured", "synced_history": 0, "synced_watchlist": 0}

    synced_history_count = 0
    synced_watchlist_count = 0

    try:
        for item in payload.history:
            client.table("user_watch_history").upsert(
                {
                    "user_id": user_id,
                    "title": item.title,
                    "clean_title": item.clean_title or item.title,
                    "year": item.year,
                    "poster_url": item.poster_url,
                    "backdrop_url": item.backdrop_url,
                    "stream_url": item.stream_url,
                    "candidate_title": item.candidate_title,
                    "quality": item.quality,
                    "progress_seconds": item.progress_seconds,
                    "duration_seconds": item.duration_seconds,
                    "completed": item.completed,
                },
                on_conflict="user_id,title",
            ).execute()
            synced_history_count += 1

        for item in payload.watchlist:
            client.table("user_watchlist").upsert(
                {
                    "user_id": user_id,
                    "title": item.title,
                    "clean_title": item.clean_title or item.title,
                    "year": item.year,
                    "rating": item.rating,
                    "poster_url": item.poster_url,
                    "backdrop_url": item.backdrop_url,
                    "overview": item.overview,
                    "genres": item.genres or [],
                },
                on_conflict="user_id,title",
            ).execute()
            synced_watchlist_count += 1

        return {
            "status": "ok",
            "synced_history": synced_history_count,
            "synced_watchlist": synced_watchlist_count,
        }
    except Exception as e:
        logger.error("Error bulk-syncing guest data for user %s: %s", user_id, str(e))
        return {
            "status": "partial",
            "synced_history": synced_history_count,
            "synced_watchlist": synced_watchlist_count,
            "error": str(e),
        }
