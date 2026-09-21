from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.services.auth import auth_service, get_current_user_optional, get_current_user_required

router = APIRouter()


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
