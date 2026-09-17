"""Services package for Cineforge backend."""
from app.services.buffering import (
    BufferHealthEngine,
    ThroughputEstimator,
    buffering_engine,
)
from app.services.media_probe import MediaProbeService, media_probe_service
from app.services.media_reader import (
    MediaReaderService,
    TelegramMediaReader,
    media_reader_service,
)
from app.services.compatibility import (
    MediaCompatibilityResult,
    MediaCompatibilityService,
    compatibility_service,
)
from app.services.remux import RemuxService, remux_service
from app.services.subtitle_service import SubtitleService, subtitle_service
from app.services.stream_session import (
    MediaChunkCache,
    MediaSessionManager,
    MediaStreamSession,
    session_manager,
)
from app.services.search_aggregator import (
    SearchAggregatorService,
    search_aggregator,
)
from app.services.telegram import telegram_service

# Inject telegram_service into media_reader_service
media_reader_service.telegram_service = telegram_service

__all__ = [
    "BufferHealthEngine",
    "MediaChunkCache",
    "MediaCompatibilityResult",
    "MediaCompatibilityService",
    "MediaProbeService",
    "MediaReaderService",
    "MediaSessionManager",
    "MediaStreamSession",
    "RemuxService",
    "SearchAggregatorService",
    "SubtitleService",
    "ThroughputEstimator",
    "buffering_engine",
    "compatibility_service",
    "media_probe_service",
    "media_reader_service",
    "remux_service",
    "search_aggregator",
    "session_manager",
    "subtitle_service",
    "telegram_service",
]
