import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.auth import auth_service, get_current_user_optional, get_current_user_required

logger = logging.getLogger("cineforge.auth")
router = APIRouter()


class ProfileUpdatePayload(BaseModel):
    full_name: Optional[str] = None
    avatar_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_auth_status():
    """Check if Supabase Auth is configured on the backend."""
    return {
        "status": "ready" if auth_service.is_configured() else "unconfigured",
        "configured": auth_service.is_configured(),
    }


@router.get("/me")
async def get_my_profile(user: Dict[str, Any] = Depends(get_current_user_required)):
    """Retrieve profile information for the currently authenticated user."""
    return {
        "status": "authenticated",
        "user": user,
    }


@router.get("/profile")
async def get_public_profile(user: Dict[str, Any] = Depends(get_current_user_required)):
    """Retrieve database profile from public.profiles table."""
    client = auth_service._get_client()
    if not client:
        return {
            "status": "unconfigured",
            "profile": {
                "id": user["id"],
                "full_name": user.get("user_metadata", {}).get("full_name") or user.get("email", "").split("@")[0],
                "avatar_id": "director",
            },
        }
    try:
        res = client.table("profiles").select("*").eq("id", user["id"]).maybe_single().execute()
        return {
            "status": "ok",
            "profile": res.data or {
                "id": user["id"],
                "full_name": user.get("user_metadata", {}).get("full_name"),
                "avatar_id": "director",
            },
        }
    except Exception as e:
        logger.warning("Error fetching profile from public.profiles: %s", str(e))
        return {
            "status": "error",
            "profile": {
                "id": user["id"],
                "full_name": user.get("user_metadata", {}).get("full_name"),
                "avatar_id": "director",
            },
        }


@router.patch("/profile")
async def update_public_profile(
    payload: ProfileUpdatePayload,
    user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Update profile details in public.profiles table."""
    client = auth_service._get_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase not configured")

    try:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        data["id"] = user["id"]
        res = client.table("profiles").upsert(data).execute()
        return {"status": "updated", "profile": res.data}
    except Exception as e:
        logger.warning("Error updating profile in public.profiles: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

