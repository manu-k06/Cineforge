from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import media_router, search_router, stream_router, telegram_router
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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(search_router, prefix="/api", tags=["Search"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(media_router, prefix="/api/telegram", tags=["Media Access & Performance"])
app.include_router(stream_router, prefix="/api/media", tags=["HTTP Media Streaming (B6)"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
