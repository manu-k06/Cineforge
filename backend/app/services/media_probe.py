import asyncio
import json
import logging
import os
import re
import shutil
import time
from fractions import Fraction
from typing import Any, Dict, Optional, Tuple

from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo

from app.config import settings
from app.models.probe import (
    BrowserCompatibilityReport,
    BufferAnalysisReport,
    PlaybackSustainabilityReport,
    ProbedMediaMetadata,
    SessionMetadataResponse,
)
from app.services.media_reader import TelegramMediaReader

logger = logging.getLogger("cineforge.media_probe")


class MediaProbeService:
    """Service to inspect media formats, evaluate browser compatibility, and assess playback sustainability."""

    def __init__(self):
        self.ffprobe_path = settings.FFPROBE_PATH

    def get_probe_binary(self) -> Tuple[Optional[str], str]:
        """Returns tuple of (binary_path, binary_type) where binary_type is 'ffprobe', 'ffmpeg', or 'none'."""
        if self.ffprobe_path and shutil.which(self.ffprobe_path):
            return self.ffprobe_path, "ffprobe"

        # Check bundled ffmpeg from imageio_ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                return ffmpeg_exe, "ffmpeg"
        except Exception:
            pass

        # Check system ffmpeg
        if shutil.which("ffmpeg"):
            return "ffmpeg", "ffmpeg"

        return None, "none"

    async def probe_media(
        self,
        reader: TelegramMediaReader,
        sample_bytes: Optional[bytes] = None,
    ) -> ProbedMediaMetadata:
        """Probe media container, codecs, and streams using ffprobe/ffmpeg if available, or Telegram metadata fallback."""
        file_name = reader.get_file_name()
        file_size = reader.get_file_size()

        # Step 1: Extract basic Telegram TL metadata as baseline
        duration_sec = None
        width = None
        height = None
        for attr in getattr(reader.document, "attributes", []):
            if isinstance(attr, DocumentAttributeVideo):
                duration_sec = getattr(attr, "duration", None)
                width = getattr(attr, "w", None)
                height = getattr(attr, "h", None)

        calculated_bitrate = None
        if duration_sec and duration_sec > 0:
            calculated_bitrate = int((file_size * 8) / duration_sec)

        # Infer container from file extension as default fallback
        lower_name = file_name.lower()
        default_container = None
        if lower_name.endswith(".mkv"):
            default_container = "matroska"
        elif lower_name.endswith(".mp4"):
            default_container = "mp4"
        elif lower_name.endswith(".webm"):
            default_container = "webm"

        binary_path, binary_type = self.get_probe_binary()

        # Step 2: Fallback if no media probe binary is available
        if binary_type == "none" or not binary_path:
            logger.info(
                "No ffprobe/ffmpeg binary found. Falling back to Telegram metadata for '%s'",
                file_name,
            )
            return ProbedMediaMetadata(
                file_name=file_name,
                file_size_bytes=file_size,
                container=default_container,
                duration_seconds=float(duration_sec) if duration_sec else None,
                width=width,
                height=height,
                frame_rate=None,
                video_codec=None,
                audio_codec=None,
                video_bitrate_bps=None,
                audio_bitrate_bps=None,
                total_bitrate_bps=calculated_bitrate,
                video_stream_count=1 if width else 0,
                audio_stream_count=1 if duration_sec else 0,
                subtitle_stream_count=0,
                probe_status="unavailable",
                probe_error="ffprobe/ffmpeg executable not found. Basic attributes extracted from Telegram metadata.",
            )

        # Step 3: Run probe on initial sample bytes (up to 2 MB)
        logger.info("Executing media probe using %s (%s) for '%s'...", binary_type, binary_path, file_name)
        t0 = time.perf_counter()

        try:
            if sample_bytes is None:
                probe_span = min(settings.PROBE_INITIAL_BYTES, file_size)
                sample_bytes = await reader.read_range(start=0, end=probe_span - 1)

            if binary_type == "ffprobe":
                proc = await asyncio.create_subprocess_exec(
                    binary_path,
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-print_format",
                    "json",
                    "-i",
                    "pipe:0",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate(input=sample_bytes)
                elapsed = time.perf_counter() - t0

                if proc.returncode != 0 and not stdout:
                    err_msg = stderr.decode("utf-8", errors="ignore").strip()
                    logger.warning("ffprobe exited with code %d: %s", proc.returncode, err_msg)
                    return ProbedMediaMetadata(
                        file_name=file_name,
                        file_size_bytes=file_size,
                        container=default_container,
                        duration_seconds=float(duration_sec) if duration_sec else None,
                        width=width,
                        height=height,
                        total_bitrate_bps=calculated_bitrate,
                        probe_status="failed",
                        probe_error=f"ffprobe failed: {err_msg}",
                    )

                data = json.loads(stdout.decode("utf-8", errors="ignore"))
                fmt = data.get("format", {})
                streams = data.get("streams", [])

                container = fmt.get("format_name") or default_container
                probed_duration = None
                if fmt.get("duration"):
                    try:
                        probed_duration = float(fmt["duration"])
                    except (ValueError, TypeError):
                        pass
                duration_final = probed_duration or (float(duration_sec) if duration_sec else None)

                probed_total_bitrate = None
                if fmt.get("bit_rate"):
                    try:
                        probed_total_bitrate = int(fmt["bit_rate"])
                    except (ValueError, TypeError):
                        pass
                if not probed_total_bitrate and duration_final and duration_final > 0:
                    probed_total_bitrate = int((file_size * 8) / duration_final)
                total_bitrate_final = probed_total_bitrate or calculated_bitrate

                video_codec = None
                audio_codec = None
                video_bitrate = None
                audio_bitrate = None
                v_width = width
                v_height = height
                frame_rate = None

                video_count = 0
                audio_count = 0
                sub_count = 0

                for st in streams:
                    codec_type = st.get("codec_type")
                    if codec_type == "video" and video_codec is None:
                        video_count += 1
                        video_codec = st.get("codec_name")
                        v_width = st.get("width") or v_width
                        v_height = st.get("height") or v_height
                        if st.get("bit_rate"):
                            try:
                                video_bitrate = int(st["bit_rate"])
                            except (ValueError, TypeError):
                                pass
                        r_frame = st.get("r_frame_rate") or st.get("avg_frame_rate")
                        if r_frame and r_frame != "0/0":
                            try:
                                frame_rate = round(float(Fraction(r_frame)), 3)
                            except Exception:
                                pass
                    elif codec_type == "video":
                        video_count += 1
                    elif codec_type == "audio" and audio_codec is None:
                        audio_count += 1
                        audio_codec = st.get("codec_name")
                        if st.get("bit_rate"):
                            try:
                                audio_bitrate = int(st["bit_rate"])
                            except (ValueError, TypeError):
                                pass
                    elif codec_type == "audio":
                        audio_count += 1
                    elif codec_type == "subtitle":
                        sub_count += 1

            else:
                # binary_type == "ffmpeg": Probe via ffmpeg -hide_banner -i pipe:0
                proc = await asyncio.create_subprocess_exec(
                    binary_path,
                    "-hide_banner",
                    "-i",
                    "pipe:0",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate(input=sample_bytes)
                elapsed = time.perf_counter() - t0
                stderr_text = stderr.decode("utf-8", errors="ignore")

                if "Input #0" not in stderr_text:
                    err_msg = stderr_text.strip()[:300]
                    logger.warning("ffmpeg stream probe failed: %s", err_msg)
                    return ProbedMediaMetadata(
                        file_name=file_name,
                        file_size_bytes=file_size,
                        container=default_container,
                        duration_seconds=float(duration_sec) if duration_sec else None,
                        width=width,
                        height=height,
                        total_bitrate_bps=calculated_bitrate,
                        probe_status="failed",
                        probe_error=f"ffmpeg probe error: {err_msg}",
                    )

                # Parse container
                container_match = re.search(r"Input #0,\s*([^,\n]+)", stderr_text)
                container = container_match.group(1).strip() if container_match else default_container

                # Parse duration
                dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr_text)
                duration_final = None
                if dur_match:
                    h, m, s = dur_match.groups()
                    duration_final = round(int(h) * 3600 + int(m) * 60 + float(s), 2)
                if not duration_final and duration_sec:
                    duration_final = float(duration_sec)

                # Parse video stream
                video_match = re.search(
                    r"Stream #\d+:\d+.*?: Video:\s*([^,\s]+).*?,\s*(\d+)x(\d+).*?,\s*(\d+\.?\d*)\s*fps",
                    stderr_text,
                )
                if video_match:
                    video_codec = video_match.group(1)
                    v_width = int(video_match.group(2))
                    v_height = int(video_match.group(3))
                    frame_rate = float(video_match.group(4))
                else:
                    video_codec_fallback = re.search(r"Stream #\d+:\d+.*?: Video:\s*([^,\s]+)", stderr_text)
                    video_codec = video_codec_fallback.group(1) if video_codec_fallback else None
                    v_width = width
                    v_height = height
                    frame_rate = None

                # Parse audio stream
                audio_match = re.search(r"Stream #\d+:\d+.*?: Audio:\s*([^,\s]+)", stderr_text)
                audio_codec = audio_match.group(1) if audio_match else None

                # Counts
                video_count = len(re.findall(r"Stream #\d+:\d+.*?: Video:", stderr_text))
                audio_count = len(re.findall(r"Stream #\d+:\d+.*?: Audio:", stderr_text))
                sub_count = len(re.findall(r"Stream #\d+:\d+.*?: Subtitle:", stderr_text))

                video_bitrate = None
                audio_bitrate = None
                if duration_final and duration_final > 0:
                    total_bitrate_final = int((file_size * 8) / duration_final)
                else:
                    total_bitrate_final = calculated_bitrate

            logger.info(
                "Media probe completed in %.2fs: container=%s, video=%s (%sx%s @ %sfps), audio=%s, bitrate=%sbps",
                elapsed,
                container,
                video_codec,
                v_width,
                v_height,
                frame_rate,
                audio_codec,
                total_bitrate_final,
            )

            return ProbedMediaMetadata(
                file_name=file_name,
                file_size_bytes=file_size,
                container=container,
                duration_seconds=duration_final,
                width=v_width,
                height=v_height,
                frame_rate=frame_rate,
                video_codec=video_codec,
                audio_codec=audio_codec,
                video_bitrate_bps=video_bitrate,
                audio_bitrate_bps=audio_bitrate,
                total_bitrate_bps=total_bitrate_final,
                video_stream_count=max(video_count, 1 if v_width else 0),
                audio_stream_count=max(audio_count, 1 if duration_final else 0),
                subtitle_stream_count=sub_count,
                probe_status="success",
                probe_error=None,
            )

        except Exception as e:
            logger.error("Unexpected error during media probe: %s", str(e))
            return ProbedMediaMetadata(
                file_name=file_name,
                file_size_bytes=file_size,
                container=default_container,
                duration_seconds=float(duration_sec) if duration_sec else None,
                width=width,
                height=height,
                total_bitrate_bps=calculated_bitrate,
                probe_status="failed",
                probe_error=str(e),
            )

    def evaluate_browser_compatibility(
        self,
        metadata: ProbedMediaMetadata,
    ) -> BrowserCompatibilityReport:
        """Evaluate HTML5 video playback compatibility based on container and audio/video codecs."""
        container = (metadata.container or "").lower()
        v_codec = (metadata.video_codec or "").lower()
        a_codec = (metadata.audio_codec or "").lower()

        # 1. Container evaluation
        container_supported = None
        if any(c in container for c in ("mp4", "mov", "m4a")):
            container_supported = True
        elif "webm" in container and "matroska" not in container:
            container_supported = True
        elif "ogg" in container:
            container_supported = True
        elif "matroska" in container:
            container_supported = False

        # 2. Video codec evaluation
        video_codec_supported = None
        if v_codec in ("h264", "avc1", "vp8", "vp9", "av1"):
            video_codec_supported = True
        elif v_codec in ("hevc", "h265"):
            video_codec_supported = False
        elif v_codec:
            video_codec_supported = False

        # 3. Audio codec evaluation
        audio_codec_supported = None
        if a_codec in ("aac", "mp3", "opus", "vorbis", "flac"):
            audio_codec_supported = True
        elif a_codec in ("ac3", "eac3", "dts", "truehd"):
            audio_codec_supported = False
        elif a_codec:
            audio_codec_supported = False

        # 4. Overall assessment & reasoned explanations
        if container_supported is True and video_codec_supported is True and audio_codec_supported is True:
            rating = "likely_supported"
            reason = (
                f"Container '{container}' with video '{v_codec}' and audio '{a_codec}' "
                f"is natively supported by HTML5 <video> across modern browsers."
            )
        elif "matroska" in container:
            rating = "likely_unsupported"
            if video_codec_supported is True and audio_codec_supported is True:
                reason = (
                    f"MKV container is not natively supported by standard HTML5 <video> elements in Chrome/Firefox/Safari "
                    f"without remuxing, although underlying codecs (video: {v_codec}, audio: {a_codec}) are compatible."
                )
            else:
                reason = (
                    f"MKV container is not natively supported by browsers, and stream codecs (video: {v_codec or 'unknown'}, "
                    f"audio: {a_codec or 'unknown'}) may require transcoding."
                )
        elif video_codec_supported is False or audio_codec_supported is False:
            rating = "likely_unsupported"
            reason = (
                f"Media codec combination (video: {v_codec or 'unknown'}, audio: {a_codec or 'unknown'}) "
                f"is unsupported by standard browser HTML5 media pipelines without transcoding."
            )
        else:
            rating = "unknown"
            reason = (
                "Detailed codec parameters could not be conclusively determined. "
                "Playback capability depends on target browser container and codec support."
            )

        logger.info("Compatibility evaluated for '%s': %s (%s)", metadata.file_name, rating, reason)

        return BrowserCompatibilityReport(
            browser_playback=rating,
            reason=reason,
            container_supported=container_supported,
            video_codec_supported=video_codec_supported,
            audio_codec_supported=audio_codec_supported,
        )

    def evaluate_playback_sustainability(
        self,
        metadata: ProbedMediaMetadata,
        source_throughput_bps: int = settings.MEASURED_SOURCE_THROUGHPUT_BPS,
        margin: float = settings.MEDIA_SUSTAINABILITY_MARGIN,
        max_buffer_bytes: int = settings.MEDIA_MAX_BUFFER_MB * 1024 * 1024,
    ) -> Tuple[PlaybackSustainabilityReport, BufferAnalysisReport, str]:
        """Compare measured Telegram source throughput against media bitrate and determine buffer strategy."""
        media_bitrate = metadata.total_bitrate_bps

        if not media_bitrate or media_bitrate <= 0:
            sustainability = PlaybackSustainabilityReport(
                source_throughput_bps=source_throughput_bps,
                media_bitrate_bps=None,
                sustainability_ratio=None,
                playback_sustainable=None,
                margin_applied=margin,
                explanation="Media bitrate is unavailable, so playback sustainability cannot be calculated mathematically.",
            )
            buffer_rep = BufferAnalysisReport(
                max_buffer_bytes=max_buffer_bytes,
                buffer_capacity_seconds=None,
                buffer_growth_rate_bps=None,
                drain_warning=None,
            )
            return sustainability, buffer_rep, "unknown"

        ratio = round(source_throughput_bps / media_bitrate, 2)
        required_with_margin = int(media_bitrate * margin)
        sustainable = source_throughput_bps >= required_with_margin

        # Buffer capacity in seconds at max memory
        buffer_capacity_sec = round((max_buffer_bytes * 8) / media_bitrate, 1)
        growth_rate_bps = source_throughput_bps - media_bitrate

        if sustainable and ratio >= 1.5:
            strategy = "realtime"
            explanation = (
                f"Source throughput ({round(source_throughput_bps/1e6, 2)} Mbps) comfortably exceeds "
                f"media bitrate ({round(media_bitrate/1e6, 2)} Mbps) with a {ratio}x ratio. Realtime streaming is sustainable."
            )
            drain_warning = None
        elif sustainable:
            strategy = "conservative_prefetch"
            explanation = (
                f"Source throughput ({round(source_throughput_bps/1e6, 2)} Mbps) satisfies media bitrate "
                f"({round(media_bitrate/1e6, 2)} Mbps) within safety margin ({ratio}x). Conservative prefetching recommended."
            )
            drain_warning = None
        elif ratio >= 0.70:
            strategy = "aggressive_prefetch"
            if growth_rate_bps >= 0:
                explanation = (
                    f"Source throughput ({round(source_throughput_bps/1e6, 2)} Mbps) marginally exceeds media bitrate "
                    f"({round(media_bitrate/1e6, 2)} Mbps, ratio {ratio}x) but is below the {margin}x safety margin. "
                    f"Buffer fills slowly; aggressive initial pre-buffering recommended."
                )
                drain_warning = None
            else:
                explanation = (
                    f"Source throughput ({round(source_throughput_bps/1e6, 2)} Mbps) is below media bitrate "
                    f"({round(media_bitrate/1e6, 2)} Mbps). Buffer will drain over time; aggressive initial pre-buffering required."
                )
                drain_warning = (
                    f"Buffer will drain at {round(abs(growth_rate_bps)/1e6, 2)} Mbps during continuous playback. "
                    f"Max buffer holds only {buffer_capacity_sec}s of video."
                )
        else:
            strategy = "unsustainable"
            explanation = (
                f"Media bitrate ({round(media_bitrate/1e6, 2)} Mbps) significantly exceeds Telegram upstream throughput "
                f"({round(source_throughput_bps/1e6, 2)} Mbps, ratio {ratio}x). Continuous playback without frequent stalls is unsustainable."
            )
            drain_warning = (
                f"Severe bandwidth deficit: buffer drains at {round(abs(growth_rate_bps)/1e6, 2)} Mbps. "
                f"Max {round(max_buffer_bytes/(1024*1024))} MB memory holds only {buffer_capacity_sec}s of playback."
            )

        logger.info(
            "Sustainability evaluated: ratio=%.2f, sustainable=%s, strategy=%s",
            ratio,
            sustainable,
            strategy,
        )

        sustainability = PlaybackSustainabilityReport(
            source_throughput_bps=source_throughput_bps,
            media_bitrate_bps=media_bitrate,
            sustainability_ratio=ratio,
            playback_sustainable=sustainable,
            margin_applied=margin,
            explanation=explanation,
        )

        buffer_rep = BufferAnalysisReport(
            max_buffer_bytes=max_buffer_bytes,
            buffer_capacity_seconds=buffer_capacity_sec,
            buffer_growth_rate_bps=growth_rate_bps,
            drain_warning=drain_warning,
        )

        return sustainability, buffer_rep, strategy

    async def get_session_metadata(
        self,
        session,
    ) -> SessionMetadataResponse:
        """Analyze a MediaStreamSession and return comprehensive probed metadata, compatibility, and sustainability."""
        # Use session-level cached probe if already computed
        if hasattr(session, "_cached_metadata_response") and session._cached_metadata_response is not None:
            return session._cached_metadata_response

        # Fetch initial chunks (chunk 0 + chunk 1 = 1 MB) into session cache for probing
        sample_bytes = session.cache.get(0)
        if not sample_bytes:
            sample_bytes = await session.fetch_chunk(0)

        chunk1 = session.cache.get(1)
        if not chunk1:
            try:
                chunk1 = await session.fetch_chunk(1)
            except Exception:
                chunk1 = b""

        combined_sample = sample_bytes + (chunk1 or b"")
        probed_meta = await self.probe_media(session.reader, sample_bytes=combined_sample)

        compatibility = self.evaluate_browser_compatibility(probed_meta)
        sustainability, buffer_rep, strategy = self.evaluate_playback_sustainability(
            metadata=probed_meta,
            max_buffer_bytes=session.cache.max_bytes,
        )

        response = SessionMetadataResponse(
            session_id=session.session_id,
            metadata=probed_meta,
            compatibility=compatibility,
            sustainability=sustainability,
            buffer=buffer_rep,
            recommended_buffer_strategy=strategy,
        )

        # Cache on the session object
        session._cached_metadata_response = response
        return response


media_probe_service = MediaProbeService()
