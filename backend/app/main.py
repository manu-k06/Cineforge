from contextlib import asynccontextmanager

import app.services.telethon_compat  # noqa: F401 - Register MTProto compatibility constructors
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import search_router, telegram_router
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


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/search/ui")
