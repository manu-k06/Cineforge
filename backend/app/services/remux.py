import asyncio
import logging
import os
import shutil
import subprocess
import threading
import time
from typing import AsyncIterator, List, Optional, Tuple

from app.config import settings
from app.services.media_probe import media_probe_service
from app.services.stream_session import MediaStreamSession

logger = logging.getLogger("cineforge.remux")


class RemuxService:
    """Manages on-the-fly progressive FFmpeg remuxing from MKV to fragmented MP4 (fMP4) for browser playback."""

    def __init__(self):
        self.custom_ffmpeg_path = settings.FFMPEG_PATH
        self.default_aac_bitrate = settings.AUDIO_AAC_BITRATE

    def get_ffmpeg_binary(self) -> str:
        """Finds and returns a valid path to an FFmpeg executable, or raises RuntimeError."""
        # 1. Configured custom path
        if self.custom_ffmpeg_path and shutil.which(self.custom_ffmpeg_path):
            return self.custom_ffmpeg_path

        # 2. System PATH
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return which_ffmpeg

        # 3. Bundled imageio_ffmpeg
        try:
            import imageio_ffmpeg

            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass

        raise RuntimeError(
            "FFmpeg executable not found on system PATH or bundled imageio_ffmpeg. "
            "Please ensure FFmpeg is installed to enable browser playback remuxing."
        )

    def determine_audio_parameters(
        self,
        audio_codec: Optional[str],
        audio_track_idx: int = 0,
    ) -> Tuple[List[str], bool]:
        """Determines whether audio can be stream-copied or must be transcoded to AAC for browser compatibility.

        Returns:
            Tuple[List[str], bool]: (ffmpeg_audio_arguments, is_transcoding)
        """
        codec_normalized = (audio_codec or "").lower().strip()

        # Browser-compatible audio codecs that can be safely stream-copied into fMP4
        browser_native_audio = {"aac", "mp3"}

        if codec_normalized in browser_native_audio:
            logger.debug("Audio codec '%s' is natively browser compatible. Using stream copy (-c:a copy).", codec_normalized)
            return ["-c:a", "copy"], False

        # Incompatible codecs (e.g. AC3, E-AC3, DTS, TrueHD, FLAC, Opus in MP4, or unknown)
        logger.info(
            "Audio codec '%s' requires browser compatibility transcoding. Using -c:a aac -b:a %s.",
            codec_normalized or "unknown",
            self.default_aac_bitrate,
        )
        return ["-c:a", "aac", "-b:a", self.default_aac_bitrate], True

    def build_remux_command(
        self,
        ffmpeg_bin: str,
        seek_seconds: float = 0.0,
        audio_codec: Optional[str] = None,
        audio_track_idx: int = 0,
    ) -> List[str]:
        """Constructs the exact FFmpeg command line arguments for zero-video-transcode fMP4 progressive output."""
        audio_args, _ = self.determine_audio_parameters(audio_codec, audio_track_idx)

        cmd = [
            ffmpeg_bin,
            "-loglevel",
            "error",
            "-nostdin",
        ]

        if seek_seconds and seek_seconds > 0.0:
            # Fast input seek before pipe demuxing skips to nearest keyframe rapidly
            cmd.extend(["-ss", f"{seek_seconds:.3f}"])

        # Input from stdin pipe
        cmd.extend(["-i", "pipe:0"])

        # Map primary video track and specified audio track if present
        cmd.extend([
            "-map",
            "0:v:0?",
            "-map",
            f"0:a:{audio_track_idx}?",
        ])

        # CRITICAL: Video is ALWAYS stream-copied (zero transcoding)
        cmd.extend(["-c:v", "copy"])

        # Audio stream copy or AAC fallback
        cmd.extend(audio_args)

        # Fragmented MP4 settings for progressive browser / MSE streaming
        cmd.extend([
            "-movflags",
            "frag_keyframe+empty_moov+default_base_moof",
            "-f",
            "mp4",
            "pipe:1",
        ])

        return cmd

    async def stream_fmp4(
        self,
        session: Any,
        seek_seconds: float = 0.0,
        audio_track_idx: int = 0,
        read_buffer_bytes: int = 65536,
    ) -> AsyncIterator[bytes]:
        """Streams progressive fragmented MP4 chunks from PlaybackSession (Go streamer) or legacy MediaStreamSession via FFmpeg stream-copy.

        Guarantees zero orphaned FFmpeg subprocesses on client disconnection or stream cancellation.
        """
        ffmpeg_bin = self.get_ffmpeg_binary()

        # Step 1A: Native Go Streamer path (PlaybackSession)
        stream_url = getattr(session, "stream_url", None)
        use_stream_url = False
        if stream_url:
            try:
                import httpx
                with httpx.Client(timeout=0.6) as hc:
                    hr = hc.head(stream_url)
                    if hr.status_code in (200, 206):
                        use_stream_url = True
            except Exception:
                use_stream_url = False

        if stream_url and use_stream_url:
            cmd = [
                ffmpeg_bin,
                "-loglevel",
                "error",
                "-nostdin",
            ]
            if seek_seconds and seek_seconds > 0.0:
                cmd.extend(["-ss", f"{seek_seconds:.3f}"])

            cmd.extend([
                "-i",
                stream_url,
                "-map",
                "0:v:0?",
                "-map",
                f"0:a:{audio_track_idx}?",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-movflags",
                "frag_keyframe+empty_moov+default_base_moof",
                "-flush_packets",
                "1",
                "-f",
                "mp4",
                "pipe:1",
            ])

            logger.info(
                "Spawning FFmpeg Go-streamer remuxer for session %s [seek=%.2fs]: %s",
                session.session_id[:8],
                seek_seconds,
                " ".join(cmd),
            )

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )

            total_fmp4_bytes = 0
            try:
                while True:
                    chunk = await asyncio.to_thread(proc.stdout.read, read_buffer_bytes)
                    if not chunk:
                        break
                    total_fmp4_bytes += len(chunk)
                    yield chunk
            except (asyncio.CancelledError, GeneratorExit):
                logger.info(
                    "Client disconnected from Go-streamer remux stream [session=%s, sent=%d bytes]",
                    session.session_id[:8],
                    total_fmp4_bytes,
                )
                raise
            except Exception as e:
                logger.error("Error during Go-streamer fMP4 remux streaming [session=%s]: %s", session.session_id[:8], str(e))
                raise
            finally:
                if proc.poll() is None:
                    try:
                        proc.terminate()
                        try:
                            proc.wait(timeout=0.5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=0.5)
                    except Exception as e:
                        logger.debug("Error while terminating FFmpeg process: %s", str(e))

                if proc.stdout and not proc.stdout.closed:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass

                if proc.stderr and not proc.stderr.closed:
                    try:
                        proc.stderr.close()
                    except Exception:
                        pass

                logger.info("FFmpeg Go-streamer remux process cleaned up successfully for session %s.", session.session_id[:8])
            return

        # Step 1B: Fallback direct streaming/remuxing path
        reader = await session.get_reader() if hasattr(session, "get_reader") else getattr(session, "reader", None)
        audio_codec = None
        if reader:
            try:
                metadata = await media_probe_service.probe_media(reader)
                audio_codec = metadata.audio_codec
            except Exception as probe_err:
                logger.debug("Remux media probe error: %s", str(probe_err))

        cmd = self.build_remux_command(
            ffmpeg_bin=ffmpeg_bin,
            seek_seconds=seek_seconds,
            audio_codec=audio_codec,
            audio_track_idx=audio_track_idx,
        )

        logger.info(
            "Spawning FFmpeg remuxer for session %s [seek=%.2fs, audio_codec=%s]: %s",
            session.session_id[:8],
            seek_seconds,
            audio_codec,
            " ".join(cmd),
        )

        # Step 2: Spawn FFmpeg subprocess
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        # Step 3: Feeder thread to write MKV stream into proc.stdin
        stop_feeder = threading.Event()
        loop = asyncio.get_running_loop()

        def _feeder_worker():
            """Reads chunks from the session and pipes into proc.stdin in a background thread."""
            try:
                start_byte = 0
                end_byte = session.file_size - 1

                gen = session.stream_byte_range(start_byte, end_byte)

                while not stop_feeder.is_set() and proc.poll() is None:
                    future = asyncio.run_coroutine_threadsafe(gen.__anext__(), loop)
                    try:
                        piece = future.result()
                    except (StopAsyncIteration, asyncio.CancelledError):
                        break
                    except Exception:
                        break

                    if proc.stdin and not proc.stdin.closed:
                        try:
                            proc.stdin.write(piece)
                            proc.stdin.flush()
                        except (BrokenPipeError, OSError, ValueError):
                            break
            except Exception as e:
                logger.debug("Feeder worker finished: %s", str(e))
            finally:
                if proc.stdin and not proc.stdin.closed:
                    try:
                        proc.stdin.close()
                    except Exception:
                        pass

        feeder_thread = threading.Thread(
            target=_feeder_worker,
            name=f"remux-feeder-{session.session_id[:8]}",
            daemon=True,
        )
        feeder_thread.start()

        # Step 4: Stream fMP4 chunks from proc.stdout to client
        total_fmp4_bytes = 0
        try:
            while True:
                # Read stdout in thread pool to prevent event loop blocking
                chunk = await asyncio.to_thread(proc.stdout.read, read_buffer_bytes)
                if not chunk:
                    # EOF reached
                    break

                total_fmp4_bytes += len(chunk)
                yield chunk

        except (asyncio.CancelledError, GeneratorExit):
            logger.info("Client disconnected from remux stream [session=%s, sent=%d bytes]", session.session_id[:8], total_fmp4_bytes)
            raise
        except Exception as e:
            logger.error("Error during fMP4 remux streaming [session=%s]: %s", session.session_id[:8], str(e))
            raise
        finally:
            # Step 5: Absolute cleanup guarantee - NO orphaned FFmpeg subprocesses
            stop_feeder.set()

            if proc.stdin and not proc.stdin.closed:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

            if proc.poll() is None:
                try:
                    proc.terminate()
                    # Wait briefly for graceful shutdown, then kill if stubborn
                    try:
                        proc.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=0.5)
                except Exception as e:
                    logger.debug("Error while terminating FFmpeg process: %s", str(e))

            if proc.stdout and not proc.stdout.closed:
                try:
                    proc.stdout.close()
                except Exception:
                    pass

            if proc.stderr and not proc.stderr.closed:
                try:
                    proc.stderr.close()
                except Exception:
                    pass

            logger.info("FFmpeg remux process cleaned up successfully for session %s.", session.session_id[:8])


remux_service = RemuxService()
