from contextlib import asynccontextmanager

import app.services.telethon_compat  # noqa: F401 - Register MTProto compatibility constructors
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai_router,
    auth_router,
    cache_router,
    metadata_router,
    search_router,
    telegram_router,
)
from app.config import settings
from app.services.telegram import telegram_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect the Telethon MTProto client
    await telegram_service.connect()
    yield
    # Shutdown: cleanly disconnect the client
    await telegram_service.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["https://cineforge-v1.vercel.app"],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(search_router, prefix="/api", tags=["Search"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(ai_router, prefix="/api/ai", tags=["CineAI"])
app.include_router(cache_router, prefix="/api/cache", tags=["Cache"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(metadata_router, prefix="/api/metadata", tags=["Metadata"])




@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/search/ui")
