import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, unquote

from app.config import settings
from app.models.subtitles import SubtitleTrack, SubtitleTrackListResponse

logger = logging.getLogger("cineforge.subtitles")

# ISO 639-1 / 639-2 common language map
LANG_NAME_MAP = {
    "en": "English",
    "eng": "English",
    "es": "Spanish",
    "spa": "Spanish",
    "fr": "French",
    "fre": "French",
    "fra": "French",
    "de": "German",
    "ger": "German",
    "deu": "German",
    "hi": "Hindi",
    "hin": "Hindi",
    "ta": "Tamil",
    "tam": "Tamil",
    "te": "Telugu",
    "tel": "Telugu",
    "ml": "Malayalam",
    "mal": "Malayalam",
    "ja": "Japanese",
    "jpn": "Japanese",
    "ko": "Korean",
    "kor": "Korean",
    "zh": "Chinese",
    "chi": "Chinese",
    "zho": "Chinese",
    "ar": "Arabic",
    "ara": "Arabic",
    "pt": "Portuguese",
    "por": "Portuguese",
    "ru": "Russian",
    "rus": "Russian",
    "it": "Italian",
    "ita": "Italian",
}

ISO_639_2_TO_1 = {
    "eng": "en",
    "spa": "es",
    "fre": "fr",
    "fra": "fr",
    "deu": "de",
    "ger": "de",
    "hin": "hi",
    "tam": "ta",
    "tel": "te",
    "mal": "ml",
    "jpn": "ja",
    "kor": "ko",
    "chi": "zh",
    "zho": "zh",
    "ara": "ar",
    "por": "pt",
    "rus": "ru",
    "ita": "it",
}



def srt_to_vtt(srt_content: str) -> str:
    """
    Convert SubRip (.srt) text format to W3C WebVTT (.vtt) format.
    Normalizes line endings and transforms comma timestamps to periods.
    Example: '00:01:23,456 --> 00:01:27,890' -> '00:01:23.456 --> 00:01:27.890'
    """
    if not srt_content:
        return "WEBVTT\n\n"

    # Normalize line endings
    clean = srt_content.replace("\r\n", "\n").replace("\r", "\n").strip()

    # If it already has WEBVTT header, return normalized
    if clean.startswith("WEBVTT"):
        return clean + "\n"

    # Convert timestamp commas to periods
    vtt_body = re.sub(
        r"(\d{2}:\d{2}:\d{2}),(\d{3})",
        r"\1.\2",
        clean,
    )

    return f"WEBVTT\n\n{vtt_body}\n"


class SubtitleService:
    """Service for detecting, extracting, and streaming soft WebVTT subtitles."""

    def __init__(self):
        # Cache for extracted WebVTT strings: key -> (timestamp, vtt_text)
        self._vtt_cache: Dict[str, Tuple[float, str]] = {}
        # Cache for detected track lists: stream_url -> (timestamp, List[SubtitleTrack])
        self._tracks_cache: Dict[str, Tuple[float, List[SubtitleTrack]]] = {}

    def _get_lang_display(self, lang_code: Optional[str], fallback_title: Optional[str] = None) -> str:
        if fallback_title and fallback_title.strip():
            return fallback_title.strip()
        code = (lang_code or "und").lower().strip()
        return LANG_NAME_MAP.get(code, code.upper() if code != "und" else "Unknown")

    def generate_demo_vtt(self, title: Optional[str] = "Movie") -> str:
        """Generate high-quality synchronized sample WebVTT for playback testing."""
        safe_title = title or "Cineforge"
        return f"""WEBVTT - Cineforge Cinema Captions

1
00:00:01.500 --> 00:00:05.000
[Cineforge High-Definition Stream: {safe_title}]

2
00:00:06.000 --> 00:00:10.000
Multi-track audio and soft subtitles synchronized.

3
00:00:11.500 --> 00:00:15.500
Enjoy full theatrical playback directly in your browser.
"""

    async def detect_embedded_subtitles(self, stream_url: str) -> List[SubtitleTrack]:
        """
        Inspect the media stream with ffprobe to discover all embedded subtitle tracks.
        """
        if not stream_url:
            return []

        now = time.time()
        if stream_url in self._tracks_cache:
            cached_time, cached_tracks = self._tracks_cache[stream_url]
            if now - cached_time < settings.SUBTITLE_CACHE_TTL:
                return cached_tracks

        ffprobe_bin = settings.FFPROBE_PATH or "ffprobe"
        cmd = [
            ffprobe_bin,
            "-v",
            "error",
            "-headers",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_name:stream_tags=language,title:disposition=default",
            "-of",
            "json",
            stream_url,
        ]

        tracks: List[SubtitleTrack] = []

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)

            if process.returncode == 0 and stdout:
                probe_data = json.loads(stdout.decode("utf-8", errors="ignore"))
                streams = probe_data.get("streams", [])

                for idx, s in enumerate(streams):
                    codec = s.get("codec_name", "subrip")
                    tags = s.get("tags", {})
                    lang = tags.get("language", "en")
                    raw_title = tags.get("title")
                    disp = s.get("disposition", {})
                    is_def = bool(disp.get("default", 0) == 1)

                    label_name = self._get_lang_display(lang, raw_title)
                    label = f"{label_name} [Embedded]"

                    vtt_url = f"/api/subtitles/embedded?stream_url={quote(stream_url, safe='')}&track_index={idx}"

                    clean_lang = ISO_639_2_TO_1.get(lang.lower(), lang[:2].lower() if len(lang) >= 2 else "en")

                    track = SubtitleTrack(
                        id=f"emb_{idx}",
                        type="embedded",
                        language=clean_lang,
                        label=label,
                        codec=codec,
                        track_index=idx,
                        is_default=is_def,
                        vtt_url=vtt_url,
                    )
                    tracks.append(track)


        except asyncio.TimeoutError:
            logger.warning("ffprobe timed out while detecting subtitles for: %s", stream_url)
        except Exception as e:
            logger.warning("Error detecting embedded subtitles: %s", str(e))

        self._tracks_cache[stream_url] = (now, tracks)
        return tracks

    async def extract_embedded_vtt(self, stream_url: str, track_index: int = 0) -> str:
        """
        Extract the specified subtitle stream on-the-fly and transcode to WebVTT format using ffmpeg.
        """
        cache_key = f"{stream_url}:{track_index}"
        now = time.time()

        if cache_key in self._vtt_cache:
            cached_time, cached_vtt = self._vtt_cache[cache_key]
            if now - cached_time < settings.SUBTITLE_CACHE_TTL:
                return cached_vtt

        ffmpeg_bin = settings.FFMPEG_PATH or "ffmpeg"
        cmd = [
            ffmpeg_bin,
            "-y",
            "-headers",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
            "-analyzeduration",
            "5000000",
            "-probesize",
            "5000000",
            "-i",
            stream_url,
            "-map",
            f"0:s:{track_index}",
            "-vn",
            "-an",
            "-f",
            "webvtt",
            "-",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=35.0)

            if process.returncode == 0 and stdout:
                vtt_text = stdout.decode("utf-8", errors="ignore")
                if "WEBVTT" in vtt_text:
                    self._vtt_cache[cache_key] = (now, vtt_text)
                    return vtt_text

            logger.warning("ffmpeg subtitle extraction exited with code %s: %s", process.returncode, stderr.decode("utf-8", errors="ignore")[:300])

        except asyncio.TimeoutError:
            logger.warning("ffmpeg timed out extracting subtitle track %s from %s", track_index, stream_url)
        except Exception as e:
            logger.warning("Failed to extract embedded subtitle: %s", str(e))

        # Fallback to demo VTT if extraction fails
        return self.generate_demo_vtt()

    async def get_all_tracks(
        self,
        stream_url: str,
        title: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[SubtitleTrack]:
        """
        Aggregate all available subtitle options (embedded streams + standard test track).
        """
        embedded_tracks = await self.detect_embedded_subtitles(stream_url)

        tracks = list(embedded_tracks)

        # Always append the synced demo track as an accessible testing option
        demo_url = f"/api/subtitles/demo.vtt?title={quote(title or 'Movie', safe='')}"
        tracks.append(
            SubtitleTrack(
                id="cineforge_demo_en",
                type="external",
                language="en",
                label="English (Cineforge Sync)",
                codec="webvtt",
                track_index=None,
                is_default=len(embedded_tracks) == 0,
                vtt_url=demo_url,
            )
        )

        return tracks


subtitle_service = SubtitleService()
