"""API Module Package."""
from app.api.media import router as media_router
from app.api.search import router as search_router
from app.api.stream import router as stream_router
from app.api.telegram import router as telegram_router

__all__ = ["media_router", "search_router", "stream_router", "telegram_router"]
