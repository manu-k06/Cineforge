"""Services package for Cineforge backend."""
from app.services.media_reader import (
    MediaReaderService,
    TelegramMediaReader,
    media_reader_service,
)
from app.services.stream_session import (
    MediaChunkCache,
    MediaSessionManager,
    MediaStreamSession,
    session_manager,
)
from app.services.telegram import telegram_service

# Inject telegram_service into media_reader_service
media_reader_service.telegram_service = telegram_service

__all__ = [
    "MediaChunkCache",
    "MediaReaderService",
    "MediaSessionManager",
    "MediaStreamSession",
    "media_reader_service",
    "session_manager",
    "telegram_service",
]
