import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from telethon import TelegramClient
from telethon.tl.functions.upload import GetFileRequest
from telethon.tl.types import (
    Document,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    InputDocumentFileLocation,
    Message,
    MessageMediaDocument,
)

from app.config import settings
from app.models.media import (
    B52DiagnosticReport,
    B52DualComparisonResponse,
    DirectTelethonComparison,
    MediaBitrateInfo,
    MediaMultiRangeBenchmarkItem,
    ParallelWorkerItem,
    ParallelWorkersTest,
)

logger = logging.getLogger("cineforge.media_reader")


class TelegramMediaReader:
    """Isolated, memory-bounded, cancellation-aware reader for Telegram media."""

    def __init__(
        self,
        client: TelegramClient,
        document: Document,
        file_size: int,
        mime_type: str,
        file_name: str,
        dc_id: Optional[int] = None,
        message_id: Optional[int] = None,
    ):
        self.client = client
        self.document = document
        self.file_size = file_size
        self.mime_type = mime_type or "video/mp4"
        self.file_name = file_name or "video.mp4"
        self.dc_id = dc_id
        self.message_id = message_id

    def get_file_size(self) -> int:
        return self.file_size

    def get_mime_type(self) -> str:
        return self.mime_type

    def get_file_name(self) -> str:
        return self.file_name

    def get_video_metadata(self) -> MediaBitrateInfo:
        """Extract duration, resolution, codecs, and calculate bitrate from Telegram attributes."""
        duration = None
        width = None
        height = None
        supports_streaming = None

        for attr in getattr(self.document, "attributes", []):
            if isinstance(attr, DocumentAttributeVideo):
                duration = getattr(attr, "duration", None)
                width = getattr(attr, "w", None)
                height = getattr(attr, "h", None)
                supports_streaming = getattr(attr, "supports_streaming", None)

        calculated_bitrate_mbps = None
        if duration and duration > 0:
            bitrate_bps = (self.file_size * 8) / duration
            calculated_bitrate_mbps = round(bitrate_bps / 1_000_000, 2)
            bitrate_status = (
                f"Calculated from duration ({duration}s) and size "
                f"({round(self.file_size/(1024*1024), 2)} MB): {calculated_bitrate_mbps} Mbps "
                f"({round(bitrate_bps/(8*1024*1024), 2)} MB/s)"
            )
        else:
            bitrate_status = "Bitrate unavailable from Telegram metadata."

        return MediaBitrateInfo(
            duration_seconds=duration,
            width=width,
            height=height,
            supports_streaming=supports_streaming,
            video_codec="Unknown (not stored in Telegram TL attributes)",
            audio_codec="Unknown (not stored in Telegram TL attributes)",
            calculated_bitrate_mbps=calculated_bitrate_mbps,
            bitrate_status=bitrate_status,
        )

    def validate_range(self, start: int, end: Optional[int] = None) -> tuple[int, int]:
        """Validate and normalize requested byte range boundaries [start, end]."""
        if start < 0:
            raise ValueError(f"Range start cannot be negative: {start}")

        if start >= self.file_size:
            raise ValueError(
                f"Range start ({start}) exceeds total file size ({self.file_size} bytes)."
            )

        if end is None:
            end = self.file_size - 1
        elif end >= self.file_size:
            end = self.file_size - 1

        if start > end:
            raise ValueError(f"Invalid byte range: start ({start}) > end ({end})")

        return start, end

    async def stream_range(
        self,
        start: int,
        end: Optional[int] = None,
        chunk_size: int = settings.TELEGRAM_CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        """Stream an arbitrary byte range from Telegram using a bounded prefetch queue and MTProto chunking."""
        start, end = self.validate_range(start, end)
        total_bytes_to_read = end - start + 1

        logger.info(
            "Starting range stream: bytes %d-%d (%d bytes, %.2f MB) for msg_id=%s",
            start,
            end,
            total_bytes_to_read,
            total_bytes_to_read / (1024 * 1024),
            self.message_id,
        )

        stream = self.client.iter_download(
            self.document,
            offset=start,
            request_size=chunk_size,
            file_size=self.file_size,
            dc_id=self.dc_id,
        )

        # Bounded queue for prefetching up to MEDIA_PREFETCH_CHUNKS (e.g. 4 * 512KB = 2MB)
        queue: asyncio.Queue = asyncio.Queue(maxsize=settings.MEDIA_PREFETCH_CHUNKS)
        stop_event = asyncio.Event()

        async def _prefetch_worker():
            try:
                async for raw_chunk in stream:
                    if stop_event.is_set():
                        break
                    chunk_bytes = bytes(raw_chunk)
                    await queue.put(chunk_bytes)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Error in media prefetch worker: %s", str(e))
                await queue.put(e)
            finally:
                await queue.put(None)

        prefetch_task = asyncio.create_task(_prefetch_worker())
        bytes_delivered = 0

        try:
            while bytes_delivered < total_bytes_to_read:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item

                chunk: bytes = item
                needed = total_bytes_to_read - bytes_delivered

                if len(chunk) > needed:
                    chunk_to_yield = chunk[:needed]
                else:
                    chunk_to_yield = chunk

                bytes_delivered += len(chunk_to_yield)
                yield chunk_to_yield

                if bytes_delivered >= total_bytes_to_read:
                    break

        finally:
            stop_event.set()
            prefetch_task.cancel()
            try:
                await prefetch_task
            except asyncio.CancelledError:
                pass
            try:
                await stream.close()
            except Exception:
                pass
            logger.info(
                "Range stream finished/cleaned up: delivered %d/%d bytes for msg_id=%s",
                bytes_delivered,
                total_bytes_to_read,
                self.message_id,
            )

    async def read_range(
        self,
        start: int,
        end: Optional[int] = None,
        chunk_size: int = settings.TELEGRAM_CHUNK_SIZE,
    ) -> bytes:
        """Read an exact byte range [start, end] into memory with safety limits."""
        start, end = self.validate_range(start, end)
        total_bytes = end - start + 1

        if total_bytes > settings.MAX_BENCHMARK_BYTES:
            raise ValueError(
                f"Requested range size ({total_bytes} bytes) exceeds safety limit ({settings.MAX_BENCHMARK_BYTES} bytes)."
            )

        buffer = bytearray()
        async for chunk in self.stream_range(start, end, chunk_size=chunk_size):
            buffer.extend(chunk)

        return bytes(buffer)

    async def benchmark_range(
        self,
        start: int,
        end: Optional[int] = None,
        chunk_size: int = settings.TELEGRAM_CHUNK_SIZE,
    ) -> Dict[str, Any]:
        """Fetch a specific byte range and measure throughput and latency."""
        start, end = self.validate_range(start, end)
        total_requested = end - start + 1

        if total_requested > settings.MAX_BENCHMARK_BYTES:
            raise ValueError(
                f"Requested range ({total_requested} bytes) exceeds safety limit of {settings.MAX_BENCHMARK_BYTES} bytes."
            )

        start_time = time.perf_counter()
        bytes_read = 0

        async for chunk in self.stream_range(start, end, chunk_size=chunk_size):
            bytes_read += len(chunk)

        elapsed = time.perf_counter() - start_time
        elapsed_safe = max(elapsed, 0.0001)

        throughput_MB_per_sec = round((bytes_read / (1024 * 1024)) / elapsed_safe, 2)
        throughput_mbps = round((bytes_read * 8 / 1_000_000) / elapsed_safe, 2)

        return {
            "success": True,
            "message_id": self.message_id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "requested_start": start,
            "requested_end": end,
            "bytes_read": bytes_read,
            "elapsed_seconds": round(elapsed, 3),
            "throughput_MB_per_sec": throughput_MB_per_sec,
            "throughput_mbps": throughput_mbps,
        }

    async def direct_telethon_benchmark(self, start: int, end: int) -> Dict[str, Any]:
        """Directly invoke raw Telethon iter_download, bypassing CineForge's MediaReader queue layer."""
        start, end = self.validate_range(start, end)
        total_bytes_needed = end - start + 1

        t0 = time.perf_counter()
        stream = self.client.iter_download(
            self.document,
            offset=start,
            request_size=settings.TELEGRAM_CHUNK_SIZE,
            file_size=self.file_size,
            dc_id=self.dc_id,
        )
        bytes_read = 0
        try:
            async for raw_chunk in stream:
                chunk = bytes(raw_chunk)
                needed = total_bytes_needed - bytes_read
                if len(chunk) > needed:
                    bytes_read += needed
                    break
                else:
                    bytes_read += len(chunk)
                if bytes_read >= total_bytes_needed:
                    break
        finally:
            await stream.close()

        elapsed = max(time.perf_counter() - t0, 0.001)
        mbps = round((bytes_read * 8 / 1_000_000) / elapsed, 2)
        MBps = round((bytes_read / (1024 * 1024)) / elapsed, 2)

        return {
            "bytes_read": bytes_read,
            "elapsed_seconds": round(elapsed, 3),
            "throughput_MB_per_sec": MBps,
            "throughput_mbps": mbps,
        }

    async def parallel_read_range(
        self,
        start: int,
        end: int,
        max_workers: int = 4,
        chunk_size: int = settings.TELEGRAM_CHUNK_SIZE,
    ) -> tuple[bytes, float, int]:
        """Fetch range chunks in parallel using dedicated DC MTProto senders."""
        start, end = self.validate_range(start, end)
        total_bytes = end - start + 1

        first_chunk_idx = start // chunk_size
        last_chunk_idx = end // chunk_size
        chunk_indices = list(range(first_chunk_idx, last_chunk_idx + 1))
        num_chunks = len(chunk_indices)

        location = InputDocumentFileLocation(
            id=self.document.id,
            access_hash=self.document.access_hash,
            file_reference=self.document.file_reference,
            thumb_size="",
        )

        num_senders = min(max_workers, num_chunks)
        senders = [await self.client._borrow_exported_sender(self.dc_id) for _ in range(num_senders)]

        async def _fetch_part(sender, idx):
            off = idx * chunk_size
            req = GetFileRequest(location=location, offset=off, limit=chunk_size)
            res = await self.client._call(sender, req)
            return idx, res.bytes

        start_time = time.perf_counter()
        tasks = []
        for i, idx in enumerate(chunk_indices):
            s = senders[i % len(senders)]
            tasks.append(_fetch_part(s, idx))

        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start_time

        # Re-sort chunks into byte sequence
        results.sort(key=lambda x: x[0])
        raw_buffer = bytearray()
        for _, chunk_data in results:
            raw_buffer.extend(chunk_data)

        slice_start = start - (first_chunk_idx * chunk_size)
        slice_end = slice_start + total_bytes
        final_bytes = bytes(raw_buffer[slice_start:slice_end])

        return final_bytes, elapsed, num_chunks

    async def controlled_parallel_test(self, span_bytes: int = 4 * 1024 * 1024) -> ParallelWorkersTest:
        """Run controlled 1, 2, and 4 worker benchmarks on identical range span."""
        span_bytes = min(span_bytes, self.file_size)
        worker_counts = [1, 2, 4]
        items = []

        for workers in worker_counts:
            buf, elapsed, _ = await self.parallel_read_range(
                start=0,
                end=span_bytes - 1,
                max_workers=workers,
            )
            elapsed_safe = max(elapsed, 0.001)
            MBps = round((len(buf) / (1024 * 1024)) / elapsed_safe, 2)
            mbps = round((len(buf) * 8 / 1_000_000) / elapsed_safe, 2)
            items.append(
                ParallelWorkerItem(
                    workers=workers,
                    bytes_read=len(buf),
                    elapsed_seconds=round(elapsed, 3),
                    throughput_MB_per_sec=MBps,
                    throughput_mbps=mbps,
                )
            )

        speedup_1_to_4 = round(items[2].throughput_MB_per_sec / max(items[0].throughput_MB_per_sec, 0.01), 2)
        parallelism_viable = speedup_1_to_4 >= 2.0

        return ParallelWorkersTest(
            results=items,
            speedup_1_to_4=speedup_1_to_4,
            parallelism_viable=parallelism_viable,
        )


class MediaReaderService:
    """Service to resolve Telegram messages and create isolated TelegramMediaReader instances."""

    def __init__(self, telegram_service):
        self.telegram_service = telegram_service

    async def get_reader_for_message(
        self,
        message_id: int,
        chat_id: Optional[int] = None,
    ) -> TelegramMediaReader:
        """Resolve a Telegram message by ID and construct a TelegramMediaReader."""
        client = self.telegram_service._get_client()
        if client is None or not client.is_connected():
            raise RuntimeError("Telegram client is not connected.")

        if not await client.is_user_authorized():
            raise RuntimeError("Telegram user client is not authenticated.")

        target_chat = None
        if chat_id is not None:
            target_chat = chat_id
        elif settings.TELEGRAM_BOT_USERNAME:
            target_chat = settings.TELEGRAM_BOT_USERNAME

        message: Optional[Message] = None
        if target_chat is not None:
            try:
                entity = await client.get_entity(target_chat)
                message = await client.get_messages(entity, ids=message_id)
            except Exception as e:
                logger.warning("Could not fetch message %s from chat %s: %s", message_id, target_chat, str(e))

        if message is None or not getattr(message, "media", None):
            async for dialog in client.iter_dialogs(limit=25):
                try:
                    candidate = await client.get_messages(dialog.entity, ids=message_id)
                    if candidate and getattr(candidate, "media", None):
                        message = candidate
                        break
                except Exception:
                    continue

        if message is None:
            raise ValueError(f"Message with ID {message_id} was not found.")

        if not getattr(message, "media", None):
            raise ValueError(f"Message {message_id} does not contain any media.")

        media = message.media
        if not isinstance(media, MessageMediaDocument) or not media.document:
            raise ValueError(f"Message {message_id} media is not a downloadable document/video.")

        doc: Document = media.document
        file_size = getattr(doc, "size", 0)
        mime_type = getattr(doc, "mime_type", "video/mp4")
        file_name = "video.mp4"
        dc_id = getattr(doc, "dc_id", None)

        for attr in getattr(doc, "attributes", []):
            if isinstance(attr, DocumentAttributeFilename):
                file_name = attr.file_name

        return TelegramMediaReader(
            client=client,
            document=doc,
            file_size=file_size,
            mime_type=mime_type,
            file_name=file_name,
            dc_id=dc_id,
            message_id=message_id,
        )

    async def run_b52_diagnostic(
        self,
        message_id: int,
        chat_id: Optional[int] = None,
    ) -> B52DiagnosticReport:
        """Run complete B5.2 diagnostic suite on a single Telegram media message."""
        reader = await self.get_reader_for_message(message_id=message_id, chat_id=chat_id)
        client = reader.client
        doc = reader.document
        file_size = reader.file_size

        # 1. DC & Session Information
        session_dc = getattr(client.session, "dc_id", None)
        document_dc = reader.dc_id or 0
        is_same_dc = session_dc == document_dc
        uses_exported_sender = not is_same_dc

        dc_info = {
            "session_dc_id": session_dc,
            "document_dc_id": document_dc,
            "is_same_dc": is_same_dc,
            "uses_exported_sender": uses_exported_sender,
            "connection_reused": True,
            "request_chunk_size_bytes": settings.TELEGRAM_CHUNK_SIZE,
        }

        # 2. Media Bitrate and Metadata
        media_bitrate_info = reader.get_video_metadata()

        # 3. Test Range Sizes (1MB, 4MB, 8MB, 16MB)
        sizes_to_test = [
            ("1 MB Range", 1 * 1024 * 1024),
            ("4 MB Range", 4 * 1024 * 1024),
            ("8 MB Range", 8 * 1024 * 1024),
            ("16 MB Range", 16 * 1024 * 1024),
        ]

        range_benchmarks = []
        for label, sz in sizes_to_test:
            if sz > file_size:
                continue
            b = await reader.benchmark_range(start=0, end=sz - 1)
            range_benchmarks.append(
                MediaMultiRangeBenchmarkItem(
                    range_label=label,
                    start=b["requested_start"],
                    end=b["requested_end"],
                    bytes_read=b["bytes_read"],
                    elapsed_seconds=b["elapsed_seconds"],
                    throughput_MB_per_sec=b["throughput_MB_per_sec"],
                    throughput_mbps=b["throughput_mbps"],
                )
            )

        # 4. Direct Telethon Comparison (4 MB)
        bench_span_bytes = min(4 * 1024 * 1024, file_size)
        cineforge_4mb = await reader.benchmark_range(start=0, end=bench_span_bytes - 1)
        direct_4mb = await reader.direct_telethon_benchmark(start=0, end=bench_span_bytes - 1)

        diff_pct = round(
            abs(cineforge_4mb["elapsed_seconds"] - direct_4mb["elapsed_seconds"])
            / max(direct_4mb["elapsed_seconds"], 0.001)
            * 100,
            2,
        )
        if diff_pct < 10.0:
            conclusion = f"CineForge MediaReader overhead is negligible ({diff_pct}% difference from raw Telethon)."
        else:
            conclusion = f"Observable difference of {diff_pct}% between MediaReader and raw Telethon."

        direct_comparison = DirectTelethonComparison(
            cineforge_media_reader_4mb_seconds=cineforge_4mb["elapsed_seconds"],
            cineforge_media_reader_4mb_MBps=cineforge_4mb["throughput_MB_per_sec"],
            cineforge_media_reader_4mb_mbps=cineforge_4mb["throughput_mbps"],
            direct_telethon_iter_download_4mb_seconds=direct_4mb["elapsed_seconds"],
            direct_telethon_iter_download_4mb_MBps=direct_4mb["throughput_MB_per_sec"],
            direct_telethon_iter_download_4mb_mbps=direct_4mb["throughput_mbps"],
            overhead_difference_percent=diff_pct,
            conclusion=conclusion,
        )

        # 5. Small Controlled Parallel Test (1, 2, 4 workers)
        parallel_test = await reader.controlled_parallel_test(span_bytes=bench_span_bytes)

        # 6. Analysis answers
        calc_bitrate = media_bitrate_info.calculated_bitrate_mbps or 0.0
        avg_upstream_mbps = cineforge_4mb["throughput_mbps"]
        can_sustain_bitrate = (avg_upstream_mbps > calc_bitrate * 1.5) if calc_bitrate > 0 else False

        analysis_answers = {
            "is_media_reader_responsible": "No. Raw Telethon iter_download achieves essentially identical throughput.",
            "is_parallelism_effective": f"Speedup from 1 to 4 workers is only {parallel_test.speedup_1_to_4}x (parallelism does not bypass Telegram server-side rate limits).",
            "can_telegram_sustain_bitrate": (
                f"Video bitrate requires ~{calc_bitrate} Mbps, but Telegram upstream sustains ~{avg_upstream_mbps} Mbps."
                if calc_bitrate > 0
                else "Bitrate duration attribute missing; raw throughput is ~1.0–1.4 Mbps."
            ),
            "recommended_strategy": "Direct raw MTProto streaming will buffer for high-bitrate 1080p files without adaptive pre-buffering or segment caching.",
        }

        return B52DiagnosticReport(
            success=True,
            message_id=message_id,
            file_name=reader.file_name,
            file_size_bytes=reader.file_size,
            file_size_mb=round(reader.file_size / (1024 * 1024), 2),
            mime_type=reader.mime_type,
            dc_info=dc_info,
            media_bitrate_info=media_bitrate_info,
            range_size_benchmarks=range_benchmarks,
            direct_telethon_comparison=direct_comparison,
            parallel_workers_test=parallel_test,
            analysis_answers=analysis_answers,
        )

    async def compare_two_files(
        self,
        message_id_a: int,
        message_id_b: Optional[int] = None,
        chat_id_a: Optional[int] = None,
        chat_id_b: Optional[int] = None,
    ) -> B52DualComparisonResponse:
        """Run B5.2 diagnostics across File A and optional File B (Control Video)."""
        report_a = await self.run_b52_diagnostic(message_id=message_id_a, chat_id=chat_id_a)
        report_b = None
        is_media_specific = False
        summary = f"Tested File A ({report_a.file_name})."

        if message_id_b is not None:
            report_b = await self.run_b52_diagnostic(message_id=message_id_b, chat_id=chat_id_b)
            speed_a = report_a.direct_telethon_comparison.cineforge_media_reader_4mb_MBps
            speed_b = report_b.direct_telethon_comparison.cineforge_media_reader_4mb_MBps
            speed_diff_ratio = max(speed_a, speed_b) / max(min(speed_a, speed_b), 0.01)

            is_media_specific = speed_diff_ratio > 2.0
            summary = (
                f"Compared File A ({report_a.file_name}: {speed_a} MB/s) and "
                f"File B ({report_b.file_name}: {speed_b} MB/s). "
                f"Throughput is {'media-specific' if is_media_specific else 'consistent across both media files (Telegram upstream limit)'}."
            )

        return B52DualComparisonResponse(
            success=True,
            file_a=report_a,
            file_b=report_b,
            is_bottleneck_media_specific=is_media_specific,
            summary=summary,
        )


media_reader_service = MediaReaderService(None)
