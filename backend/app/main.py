from contextlib import asynccontextmanager

import app.services.telethon_compat  # noqa: F401 - Register MTProto compatibility constructors
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai_router,
    auth_router,
    cache_router,
    history_router,
    metadata_router,
    search_router,
    subtitles_router,
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
app.include_router(history_router, prefix="/api", tags=["History & Watchlist"])
app.include_router(metadata_router, prefix="/api/metadata", tags=["Metadata"])
app.include_router(subtitles_router, prefix="/api/subtitles", tags=["Subtitles"])

import httpx
from fastapi import Request
from starlette.responses import StreamingResponse

STREAMER_LOCAL_URL = "http://127.0.0.1:8088"


@app.api_route("/stream/{path:path}", methods=["GET", "HEAD"])
@app.api_route("/watch/{path:path}", methods=["GET", "HEAD"])
@app.api_route("/download/{path:path}", methods=["GET", "HEAD"])
async def proxy_to_streamer(request: Request, path: str):
    """Proxy video streaming and download range requests to local Go FileStreamBot."""
    target_url = f"{STREAMER_LOCAL_URL}{request.url.path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    client = httpx.AsyncClient(timeout=60.0)
    req = client.build_request(
        method=request.method,
        url=target_url,
        headers=headers,
    )
    resp = await client.send(req, stream=True)

    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
    if "content-length" in resp.headers:
        response_headers["content-length"] = resp.headers["content-length"]

    async def body_stream():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        body_stream(),
        status_code=resp.status_code,
        headers=response_headers,
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/search/ui")
