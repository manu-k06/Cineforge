import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.models.probe import SubtitleTrackInfo
from app.services.remux import remux_service

logger = logging.getLogger("cineforge.subtitles")


class SubtitleService:
    """Service to discover and extract embedded subtitle streams from media sessions as WebVTT."""

    def __init__(self):
        self._vtt_cache: Dict[str, str] = {}  # {f"{session_id}:{track_id}": vtt_content}
        self.ffprobe_bin = getattr(settings, "FFPROBE_PATH", None) or shutil.which("ffprobe")

    def _get_ffprobe(self) -> Optional[str]:
        if self.ffprobe_bin and shutil.which(self.ffprobe_bin):
            return self.ffprobe_bin
        return shutil.which("ffprobe")

    def _get_ffmpeg(self) -> str:
        return remux_service.get_ffmpeg_binary()

    async def get_subtitle_tracks(self, session) -> List[SubtitleTrackInfo]:
        """Discovers all subtitle streams embedded inside the session's media."""
        if hasattr(session, "_cached_subtitle_tracks") and session._cached_subtitle_tracks is not None:
            return session._cached_subtitle_tracks

        tracks: List[SubtitleTrackInfo] = []
        stream_url = getattr(session, "stream_url", None)
        ffprobe_exe = self._get_ffprobe()

        if ffprobe_exe and stream_url:
            # Fast liveness pre-check: avoid waiting 5s if mock or offline URL
            if stream_url.startswith(("http://", "https://")):
                try:
                    with httpx.Client(timeout=0.4) as hc:
                        hr = hc.head(stream_url)
                        if hr.status_code not in (200, 206):
                            session._cached_subtitle_tracks = tracks
                            return tracks
                except Exception:
                    session._cached_subtitle_tracks = tracks
                    return tracks

            try:
                cmd = [
                    ffprobe_exe,
                    "-v",
                    "error",
                    "-select_streams",
                    "s",
                    "-show_entries",
                    "stream=index,codec_name:stream_tags=language,title",
                    "-of",
                    "json",
                    stream_url,
                ]

                def run_probe():
                    return subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5.0,
                    )

                proc = await asyncio.to_thread(run_probe)
                if proc.returncode == 0 and proc.stdout:
                    data = json.loads(proc.stdout.decode("utf-8", errors="ignore"))
                    streams = data.get("streams", [])
                    for sub_id, st in enumerate(streams):
                        codec = st.get("codec_name", "unknown")
                        stream_index = st.get("index", sub_id)
                        tags = st.get("tags") or {}
                        lang = tags.get("language") or tags.get("LANGUAGE") or f"Track {sub_id + 1}"
                        title = tags.get("title") or tags.get("TITLE")

                        # Text-based vs bitmap
                        is_text = codec.lower() in {
                            "subrip",
                            "srt",
                            "ass",
                            "ssa",
                            "webvtt",
                            "mov_text",
                            "text",
                        }

                        display_title = title if title else f"{lang.upper()} ({codec})"

                        tracks.append(
                            SubtitleTrackInfo(
                                track_id=sub_id,
                                stream_index=stream_index,
                                codec=codec,
                                is_text=is_text,
                                language=lang,
                                title=display_title,
                                vtt_url=f"/api/media/session/{session.session_id}/subtitles/{sub_id}.vtt",
                            )
                        )
            except Exception as e:
                logger.warning(
                    "ffprobe subtitle discovery failed for session %s: %s",
                    session.session_id[:8],
                    str(e),
                )

        session._cached_subtitle_tracks = tracks
        return tracks

    async def extract_vtt(self, session, track_id: int) -> str:
        """Extracts the specified subtitle track on-demand and returns standard WebVTT text."""
        cache_key = f"{session.session_id}:{track_id}"
        if cache_key in self._vtt_cache:
            return self._vtt_cache[cache_key]

        stream_url = getattr(session, "stream_url", None)
        if not stream_url:
            return "WEBVTT\n\nNOTE: Stream URL not available for subtitle extraction.\n"

        ffmpeg_bin = self._get_ffmpeg()
        cmd = [
            ffmpeg_bin,
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            stream_url,
            "-map",
            f"0:s:{track_id}",
            "-f",
            "webvtt",
            "pipe:1",
        ]

        logger.info(
            "Extracting subtitle track 0:s:%d for session %s: %s",
            track_id,
            session.session_id[:8],
            " ".join(cmd),
        )

        def run_extract():
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15.0,
            )

        try:
            proc = await asyncio.to_thread(run_extract)
            if proc.returncode == 0 and proc.stdout:
                vtt_text = proc.stdout.decode("utf-8", errors="ignore")
                if not vtt_text.startswith("WEBVTT"):
                    vtt_text = "WEBVTT\n\n" + vtt_text
                self._vtt_cache[cache_key] = vtt_text
                return vtt_text
            else:
                err_msg = proc.stderr.decode("utf-8", errors="ignore").strip()
                logger.warning(
                    "FFmpeg subtitle extraction returned non-zero (%d): %s",
                    proc.returncode,
                    err_msg,
                )
                fallback = "WEBVTT\n\nNOTE: Subtitle stream extraction could not be completed.\n"
                return fallback
        except Exception as e:
            logger.error("Exception extracting subtitle for session %s: %s", session.session_id[:8], str(e))
            return f"WEBVTT\n\nNOTE: Error extracting subtitles: {str(e)}\n"


subtitle_service = SubtitleService()
