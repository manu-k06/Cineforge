import asyncio
import collections
import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from app.config import settings
from app.models.buffering import SessionBufferingMetrics
from app.models.stream import CreateMediaSessionResponse, MediaSessionMetrics
from app.services.buffering import ThroughputEstimator, buffering_engine
from app.services.media_reader import TelegramMediaReader

logger = logging.getLogger("cineforge.stream_session")


class MediaChunkCache:
    """Bounded per-session LRU chunk cache for 512 KB Telegram media blocks."""

    def __init__(
        self,
        max_bytes: int = settings.MEDIA_MAX_BUFFER_MB * 1024 * 1024,
        chunk_size: int = settings.TELEGRAM_CHUNK_SIZE,
    ):
        self.max_bytes = max_bytes
        self.chunk_size = chunk_size
        self.max_chunks = max(1, max_bytes // chunk_size)
        self._cache: collections.OrderedDict[int, bytes] = collections.OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, chunk_idx: int) -> Optional[bytes]:
        """Retrieve chunk from cache, marking it as most recently used."""
        if chunk_idx in self._cache:
            self._cache.move_to_end(chunk_idx)
            self.hits += 1
            return self._cache[chunk_idx]
        self.misses += 1
        return None

    def put(self, chunk_idx: int, data: bytes) -> None:
        """Insert chunk into cache, evicting the oldest chunk if max capacity is exceeded."""
        if chunk_idx in self._cache:
            self._cache.move_to_end(chunk_idx)
            self._cache[chunk_idx] = data
            return

        while len(self._cache) >= self.max_chunks:
            evicted_idx, _ = self._cache.popitem(last=False)
            logger.debug("LRU evicted chunk index %d from session cache", evicted_idx)

        self._cache[chunk_idx] = data

    def has(self, chunk_idx: int) -> bool:
        return chunk_idx in self._cache

    @property
    def cached_count(self) -> int:
        return len(self._cache)

    @property
    def cached_bytes(self) -> int:
        return len(self._cache) * self.chunk_size

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 3) if total > 0 else 0.0

    def clear(self) -> None:
        self._cache.clear()


class MediaStreamSession:
    """Represents an active, isolated HTTP streaming session for a single Telegram media item."""

    def __init__(
        self,
        session_id: str,
        reader: TelegramMediaReader,
        max_buffer_mb: int = settings.MEDIA_MAX_BUFFER_MB,
    ):
        self.session_id = session_id
        self.reader = reader
        self.chunk_size = settings.TELEGRAM_CHUNK_SIZE
        self.cache = MediaChunkCache(max_bytes=max_buffer_mb * 1024 * 1024, chunk_size=self.chunk_size)
        self.created_at = time.time()
        self.last_accessed_at = time.time()
        self.total_bytes_served = 0
        self.last_requested_range: Optional[str] = None
        self.throughput_estimator = ThroughputEstimator()
        self.cached_bitrate_bps: Optional[int] = None
        self._cached_metadata_response: Optional[Any] = None
        self._in_flight_fetches: Dict[int, asyncio.Future[bytes]] = {}
        self._prefetch_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def file_size(self) -> int:
        return self.reader.get_file_size()

    @property
    def mime_type(self) -> str:
        return self.reader.get_mime_type()

    @property
    def file_name(self) -> str:
        return self.reader.get_file_name()

    def touch(self) -> None:
        self.last_accessed_at = time.time()

    def is_expired(self, timeout_seconds: float = settings.MEDIA_SESSION_TIMEOUT) -> bool:
        return (time.time() - self.last_accessed_at) > timeout_seconds

    async def get_chunk(self, chunk_idx: int) -> bytes:
        """Get chunk from LRU cache or fetch from Telegram with request deduplication and throughput tracking."""
        self.touch()

        # 1. Fast path: Memory Cache Hit
        cached = self.cache.get(chunk_idx)
        if cached is not None:
            logger.info("Cache hit for chunk %d [session=%s]", chunk_idx, self.session_id[:8])
            return cached

        logger.info("Cache miss for chunk %d [session=%s], fetching from Telegram...", chunk_idx, self.session_id[:8])

        # 2. In-flight fetch deduplication
        future: Optional[asyncio.Future[bytes]] = None
        is_initiator = False

        async with self._lock:
            if chunk_idx in self._in_flight_fetches:
                future = self._in_flight_fetches[chunk_idx]
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._in_flight_fetches[chunk_idx] = future
                is_initiator = True

        if not is_initiator:
            # Another concurrent request is already fetching this chunk
            return await future

        # 3. Initiator fetches chunk from Telegram
        try:
            start_byte = chunk_idx * self.chunk_size
            end_byte = min(start_byte + self.chunk_size - 1, self.file_size - 1)

            t0 = time.perf_counter()
            chunk_data = await self.reader.read_range(start=start_byte, end=end_byte)
            elapsed = time.perf_counter() - t0

            # Record download measurement for dynamic throughput estimation
            self.throughput_estimator.record_sample(len(chunk_data), elapsed)

            logger.info(
                "Telegram fetch completed for chunk %d (%d bytes in %.2fs, est_speed=%sbps) [session=%s]",
                chunk_idx,
                len(chunk_data),
                elapsed,
                self.throughput_estimator.get_estimated_throughput_bps(),
                self.session_id[:8],
            )

            self.cache.put(chunk_idx, chunk_data)
            future.set_result(chunk_data)
            return chunk_data
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                self._in_flight_fetches.pop(chunk_idx, None)

    def get_buffering_metrics(self) -> SessionBufferingMetrics:
        """Return dynamic playback viability and buffer health metrics."""
        bitrate = self.cached_bitrate_bps
        if not bitrate:
            meta = self.reader.get_video_metadata()
            if meta.duration_seconds and meta.duration_seconds > 0:
                bitrate = int((self.file_size * 8) / meta.duration_seconds)
                self.cached_bitrate_bps = bitrate

        return buffering_engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=self.throughput_estimator.total_downloaded_bytes,
            buffered_bytes=self.cache.cached_bytes,
            max_buffer_bytes=self.cache.max_bytes,
            download_throughput_bps=self.throughput_estimator.get_estimated_throughput_bps(),
            playback_bitrate_bps=bitrate,
        )

    def trigger_adaptive_prefetch(self, last_chunk_idx: int) -> None:
        """Trigger background prefetching of the next chunks ahead of current playhead using dynamic buffering engine."""
        buff_metrics = self.get_buffering_metrics()

        if not buff_metrics.prefetch_recommended or buff_metrics.recommended_prefetch_chunks <= 0:
            logger.debug(
                "Adaptive prefetch skipped: action=%s, health=%s [session=%s]",
                buff_metrics.prefetch_action,
                buff_metrics.buffer_health,
                self.session_id[:8],
            )
            return

        num_ahead = buff_metrics.recommended_prefetch_chunks
        total_chunks = (self.file_size + self.chunk_size - 1) // self.chunk_size

        chunks_to_prefetch = []
        for offset in range(1, num_ahead + 1):
            next_idx = last_chunk_idx + offset
            if next_idx < total_chunks and not self.cache.has(next_idx):
                chunks_to_prefetch.append(next_idx)

        if not chunks_to_prefetch:
            return

        if self._prefetch_task and not self._prefetch_task.done():
            self._prefetch_task.cancel()

        async def _prefetch_worker():
            for c_idx in chunks_to_prefetch:
                try:
                    logger.debug("Prefetching chunk %d ahead [session=%s]", c_idx, self.session_id[:8])
                    await self.get_chunk(c_idx)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning("Prefetch failed for chunk %d: %s", c_idx, str(e))
                    break

        self._prefetch_task = asyncio.create_task(_prefetch_worker())

    async def stream_byte_range(self, start: int, end: int) -> AsyncIterator[bytes]:
        """Stream the exact byte span [start, end] chunk-by-chunk with caching and prefetching."""
        self.touch()
        self.last_requested_range = f"bytes={start}-{end}"
        total_bytes_to_serve = end - start + 1

        first_chunk_idx = start // self.chunk_size
        last_chunk_idx = end // self.chunk_size

        logger.info(
            "Serving stream range bytes %d-%d (%d bytes, chunks %d..%d) [session=%s]",
            start,
            end,
            total_bytes_to_serve,
            first_chunk_idx,
            last_chunk_idx,
            self.session_id[:8],
        )

        # Trigger adaptive prefetch ahead of requested window
        self.trigger_adaptive_prefetch(last_chunk_idx)

        bytes_sent = 0
        try:
            for chunk_idx in range(first_chunk_idx, last_chunk_idx + 1):
                chunk_data = await self.get_chunk(chunk_idx)

                # Calculate slice boundaries for this chunk
                chunk_start_byte = chunk_idx * self.chunk_size
                slice_start = max(0, start - chunk_start_byte)
                slice_end = min(len(chunk_data), end - chunk_start_byte + 1)

                piece = chunk_data[slice_start:slice_end]
                bytes_sent += len(piece)
                self.total_bytes_served += len(piece)

                yield piece

                if bytes_sent >= total_bytes_to_serve:
                    break
        except asyncio.CancelledError:
            logger.info("Client disconnected from stream [session=%s, bytes_sent=%d]", self.session_id[:8], bytes_sent)
            raise
        except Exception as e:
            logger.error("Error while streaming range [session=%s]: %s", self.session_id[:8], str(e))
            raise

    def get_metrics(self) -> MediaSessionMetrics:
        """Return real-time observability metrics for this session."""
        return MediaSessionMetrics(
            session_id=self.session_id,
            file_name=self.file_name,
            file_size_bytes=self.file_size,
            cached_chunks_count=self.cache.cached_count,
            cached_bytes=self.cache.cached_bytes,
            max_buffer_bytes=self.cache.max_bytes,
            cache_hits=self.cache.hits,
            cache_misses=self.cache.misses,
            cache_hit_ratio=self.cache.hit_ratio,
            total_bytes_served=self.total_bytes_served,
            last_requested_range=self.last_requested_range,
            created_at=self.created_at,
            last_accessed_at=self.last_accessed_at,
        )

    async def close(self) -> None:
        """Clean up all in-flight workers and free cache memory."""
        if self._prefetch_task and not self._prefetch_task.done():
            self._prefetch_task.cancel()
        self.cache.clear()
        logger.info("Session %s closed and memory cache cleared.", self.session_id[:8])


class MediaSessionManager:
    """Manages active MediaStreamSession instances with expiration and memory cleanup."""

    def __init__(self):
        self._sessions: Dict[str, MediaStreamSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, reader: TelegramMediaReader) -> CreateMediaSessionResponse:
        """Create a new isolated MediaStreamSession and register it."""
        session_id = str(uuid.uuid4())
        session = MediaStreamSession(session_id=session_id, reader=reader)

        async with self._lock:
            # Evict any expired sessions
            self._cleanup_expired_locked()
            self._sessions[session_id] = session

        logger.info(
            "Created MediaStreamSession [session=%s, file=%s, size=%d bytes]",
            session_id[:8],
            session.file_name,
            session.file_size,
        )

        return CreateMediaSessionResponse(
            session_id=session_id,
            file_name=session.file_name,
            mime_type=session.mime_type,
            size=session.file_size,
            stream_url=f"/api/media/stream/{session_id}",
        )

    async def get_session(self, session_id: str) -> Optional[MediaStreamSession]:
        """Lookup active session, validating expiration."""
        async with self._lock:
            self._cleanup_expired_locked()
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    async def remove_session(self, session_id: str) -> bool:
        """Explicitly destroy session and free cache memory."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await session.close()
                return True
            return False

    def _cleanup_expired_locked(self) -> None:
        """Internal helper to remove expired sessions while holding lock."""
        expired_ids = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired_ids:
            s = self._sessions.pop(sid)
            asyncio.create_task(s.close())
            logger.info("Evicted expired session %s due to inactivity.", sid[:8])


session_manager = MediaSessionManager()
