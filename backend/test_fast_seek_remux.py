import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service
from app.services.media_reader import media_reader_service
from app.services.media_probe import media_probe_service
from app.services.stream_session import session_manager


async def test_fast_seek():
    print("Connecting Telegram...")
    await telegram_service.connect()
    reader = await media_reader_service.get_reader_for_message(message_id=9763, chat_id="me")
    session_resp = await session_manager.create_session(reader)
    session = await session_manager.get_session(session_resp.session_id)

    metadata = await media_probe_service.get_session_metadata(session)
    total_dur = metadata.metadata.duration_seconds or 7360.0
    total_size = session.file_size

    # Let's test segment 50 (300 seconds into movie)
    target_time = 300.0
    seg_dur = 6.0
    estimated_byte = int((target_time / total_dur) * total_size)
    print(f"Target time={target_time}s, Total size={total_size} bytes, Estimated byte={estimated_byte} (Chunk {estimated_byte // (512*1024)})")

    # Let's see: if we fetch chunks 0..1 (header) and chunks around estimated_byte (e.g. est_byte - 1MB to est_byte + 2MB)
    header_bytes = await session.reader.read_range(0, 1048575)  # 1 MB header
    seek_start_byte = max(1048576, estimated_byte - 1048576)
    seek_end_byte = min(total_size - 1, estimated_byte + 2097152)

    print(f"Fetching seek range bytes {seek_start_byte} to {seek_end_byte} ({round((seek_end_byte - seek_start_byte)/1024, 1)} KB)...")
    cluster_bytes = await session.reader.read_range(seek_start_byte, seek_end_byte)

    input_data = header_bytes + cluster_bytes

    cmd = [
        "ffmpeg", "-loglevel", "info", "-nostdin",
        "-ss", f"{target_time:.3f}",
        "-t", f"{seg_dur:.3f}",
        "-i", "pipe:0",
        "-c:v", "copy",
        "-c:a", "copy",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4",
        "pipe:1"
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_out, stderr_out = proc.communicate(input=input_data)
    print(f"FFmpeg stdout size: {len(stdout_out)} bytes")
    print(f"FFmpeg stderr: {stderr_out.decode('utf-8', errors='ignore')[:500]}")

    if stdout_out:
        # Check segment with ffprobe
        p = subprocess.Popen(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name", "-of", "json", "-i", "pipe:0"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = p.communicate(input=stdout_out)
        print("Probe of fast-generated segment:", out.decode("utf-8"))

    await session.close()


if __name__ == "__main__":
    asyncio.run(test_fast_seek())
