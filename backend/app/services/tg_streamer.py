import logging
import math
from typing import AsyncIterator, Optional

from telethon import TelegramClient
from telethon.tl.types import Document

logger = logging.getLogger("cineforge.tg_streamer")


class TGFileStreamer:
    """High-performance MTProto streaming engine modelled directly on TG-FileStreamBot.

    Features:
    - Zero per-chunk connection teardowns / no repeated sender-borrowing thrash.
    - True RFC 7233 byte-range streaming (unbounded 206 Partial Content).
    - Precise chunk alignment and byte-slicing matching megadlbot_oss / WebStreamer.
    - Graceful cancellation on player seek / disconnect.
    """

    DEFAULT_CHUNK_SIZE = 512 * 1024  # 512 KB MTProto chunk size

    @staticmethod
    async def yield_file(
        client: TelegramClient,
        document: Document,
        start: int,
        end: int,
        file_size: int,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        dc_id: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Stream byte range [start, end] from Telegram MTProto in a single continuous pipeline.

        Args:
            client: Active, connected Telethon TelegramClient.
            document: Telegram Document media TL object.
            start: Start byte offset (0-indexed).
            end: End byte offset (inclusive).
            file_size: Total file size in bytes.
            chunk_size: MTProto request chunk size (default: 512 KB).
            dc_id: Optional DC ID where media document resides.

        Yields:
            bytes: Byte slices matching the requested range.
        """
        if start < 0 or start > end or start >= file_size:
            return

        end = min(end, file_size - 1)
        req_length = end - start + 1

        # Align start offset to chunk boundary
        offset = start - (start % chunk_size)
        first_part_cut = start - offset

        # Total chunks to fetch from Telegram
        bytes_from_offset = end - offset + 1
        part_count = math.ceil(bytes_from_offset / chunk_size)

        logger.info(
            "TGFileStreamer starting: range=%d-%d (%d bytes), offset=%d, parts=%d, chunk_size=%d, dc_id=%s",
            start,
            end,
            req_length,
            offset,
            part_count,
            chunk_size,
            dc_id,
        )

        stream = client.iter_download(
            document,
            offset=offset,
            request_size=chunk_size,
            file_size=file_size,
            dc_id=dc_id,
        )

        current_part = 1
        bytes_yielded = 0

        try:
            async for chunk in stream:
                if not chunk:
                    break

                chunk_bytes = bytes(chunk)

                if part_count == 1:
                    slice_data = chunk_bytes[first_part_cut : first_part_cut + req_length]
                    if slice_data:
                        bytes_yielded += len(slice_data)
                        yield slice_data
                    break
                elif current_part == 1:
                    slice_data = chunk_bytes[first_part_cut:]
                    if slice_data:
                        bytes_yielded += len(slice_data)
                        yield slice_data
                elif current_part == part_count:
                    remaining = req_length - bytes_yielded
                    slice_data = chunk_bytes[:remaining]
                    if slice_data:
                        bytes_yielded += len(slice_data)
                        yield slice_data
                    break
                else:
                    bytes_yielded += len(chunk_bytes)
                    yield chunk_bytes

                current_part += 1
                if bytes_yielded >= req_length or current_part > part_count:
                    break
        except GeneratorExit:
            logger.info(
                "TGFileStreamer: client disconnected / seeked (yielded %d / %d bytes)",
                bytes_yielded,
                req_length,
            )
        except Exception as e:
            logger.warning(
                "TGFileStreamer stream error: %s (yielded %d / %d bytes)",
                str(e),
                bytes_yielded,
                req_length,
            )
            raise
        finally:
            try:
                await stream.close()
            except Exception:
                pass
            logger.debug(
                "TGFileStreamer stream finished: %d / %d bytes yielded",
                bytes_yielded,
                req_length,
            )
