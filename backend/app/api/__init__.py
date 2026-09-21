from app.api.ai import router as ai_router
from app.api.search import router as search_router
from app.api.telegram import router as telegram_router

__all__ = ["ai_router", "search_router", "telegram_router"]
