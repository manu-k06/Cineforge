import logging
from typing import Any, Dict, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger("cineforge.auth")
security = HTTPBearer(auto_error=False)


class AuthService:
    """Service for validating Supabase JWT tokens and retrieving user profiles."""

    def __init__(self):
        self._client = None

    def is_configured(self) -> bool:
        return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)

    def _get_client(self):
        if not self.is_configured():
            return None
        if self._client is not None:
            return self._client
        try:
            from supabase import create_client
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            return self._client
        except Exception as e:
            logger.warning("Failed to initialize Supabase client for Auth: %s", str(e))
            return None

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Supabase JWT token and return authenticated user metadata."""
        if not token:
            return None

        client = self._get_client()
        if not client:
            logger.debug("Supabase not configured on backend; skipping token validation.")
            return None

        try:
            user_response = client.auth.get_user(token)
            if user_response and getattr(user_response, "user", None):
                u = user_response.user
                return {
                    "id": getattr(u, "id", None),
                    "email": getattr(u, "email", None),
                    "user_metadata": getattr(u, "user_metadata", {}) or {},
                    "app_metadata": getattr(u, "app_metadata", {}) or {},
                }
        except Exception as e:
            logger.warning("Supabase token verification failed: %s", str(e))
            return None

        return None


auth_service = AuthService()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for optionally authenticated endpoints."""
    if not credentials:
        return None
    token = credentials.credentials
    return auth_service.verify_token(token)


async def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Dict[str, Any]:
    """FastAPI dependency for strictly protected endpoints."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    user = auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
