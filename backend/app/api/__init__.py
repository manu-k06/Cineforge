from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.cache import router as cache_router
from app.api.history import router as history_router
from app.api.metadata import router as metadata_router
from app.api.search import router as search_router
from app.api.subtitles import router as subtitles_router
from app.api.telegram import router as telegram_router

__all__ = [
    "ai_router",
    "auth_router",
    "cache_router",
    "history_router",
    "metadata_router",
    "search_router",
    "subtitles_router",
    "telegram_router",
]



