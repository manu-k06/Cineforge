import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.buffering import BufferHealthState, SessionBufferingMetrics
from app.services.remux import RemuxService, remux_service
from app.services.stream_session import MediaStreamSession, session_manager


class TestMilestoneB9BrowserPlayback(unittest.TestCase):
    """Comprehensive test suite for Milestone B9: Browser Playback, FFmpeg Remuxing, Seeking, and Video.js integration."""

    def setUp(self):
        self.client = TestClient(app)
        self.remux = RemuxService()
        self.file_size = 1125702788
        self.session_id = "test-b9-session-uuid"

        # Mock reader
        self.mock_reader = MagicMock()
        self.mock_reader.get_file_size.return_value = self.file_size
        self.mock_reader.get_mime_type.return_value = "video/x-matroska"
        self.mock_reader.get_file_name.return_value = "Inception.mkv"
        self.mock_reader.get_video_metadata.return_value = MagicMock(duration_seconds=8888.06)
        self.mock_reader.read_range = AsyncMock(return_value=b"\x00" * 524288)

        # Create session
        self.session = MediaStreamSession(
            session_id=self.session_id,
            reader=self.mock_reader,
            max_buffer_mb=16,
        )
        self.session.cache.put(0, b"\x00" * 524288)
        self.session.throughput_estimator.record_sample(1048576, 8.0)
        session_manager._sessions[self.session_id] = self.session

    def tearDown(self):
        session_manager._sessions.pop(self.session_id, None)

    def test_01_ffmpeg_availability_detection(self):
        """1. Verify FFmpeg binary detection finds executable or raises expected error."""
        bin_path = self.remux.get_ffmpeg_binary()
        self.assertIsNotNone(bin_path)
        self.assertTrue(len(bin_path) > 0)

    def test_02_compatible_h264_remux_configuration(self):
        """2. Verify compatible H.264 video uses stream copy (-c:v copy)."""
        cmd = self.remux.build_remux_command(
            ffmpeg_bin="ffmpeg",
            seek_seconds=0.0,
            audio_codec="aac",
        )
        self.assertIn("-c:v", cmd)
        idx = cmd.index("-c:v")
        self.assertEqual(cmd[idx + 1], "copy")

    def test_03_fragmented_mp4_output_flags(self):
        """3. Verify command generates fMP4 flags for browser progressive streaming."""
        cmd = self.remux.build_remux_command(
            ffmpeg_bin="ffmpeg",
            seek_seconds=0.0,
            audio_codec="aac",
        )
        self.assertIn("-movflags", cmd)
        idx = cmd.index("-movflags")
        self.assertEqual(cmd[idx + 1], "frag_keyframe+empty_moov+default_base_moof")
        self.assertIn("-f", cmd)
        idx_f = cmd.index("-f")
        self.assertEqual(cmd[idx_f + 1], "mp4")
        self.assertEqual(cmd[-1], "pipe:1")

    def test_04_audio_codec_decision_native_passthrough(self):
        """4. Verify native browser audio (AAC / MP3) uses stream copy."""
        args_aac, trans_aac = self.remux.determine_audio_parameters("aac")
        self.assertEqual(args_aac, ["-c:a", "copy"])
        self.assertFalse(trans_aac)

        args_mp3, trans_mp3 = self.remux.determine_audio_parameters("mp3")
        self.assertEqual(args_mp3, ["-c:a", "copy"])
        self.assertFalse(trans_mp3)

    def test_05_unsupported_audio_aac_fallback(self):
        """5. Verify unsupported audio (AC3, DTS, etc.) falls back to AAC transcoding."""
        for unsupported in ["ac3", "eac3", "dts", "truehd", "flac", None]:
            args, is_trans = self.remux.determine_audio_parameters(unsupported)
            self.assertEqual(args[0], "-c:a")
            self.assertEqual(args[1], "aac")
            self.assertIn("-b:a", args)
            self.assertTrue(is_trans)

    def test_06_video_remains_stream_copied_when_audio_transcoded(self):
        """6. Verify video remains -c:v copy even when audio is transcoded from AC3/DTS."""
        cmd = self.remux.build_remux_command(
            ffmpeg_bin="ffmpeg",
            seek_seconds=0.0,
            audio_codec="ac3",
        )
        # Video is copied
        idx_v = cmd.index("-c:v")
        self.assertEqual(cmd[idx_v + 1], "copy")
        # Audio is transcoded to aac
        idx_a = cmd.index("-c:a")
        self.assertEqual(cmd[idx_a + 1], "aac")

    def test_07_playback_endpoint_content_type_and_headers(self):
        """7. Verify GET /api/media/session/{session_id}/play.mp4 returns video/mp4 headers."""
        with patch.object(remux_service, "stream_fmp4") as mock_stream:
            async def _fake_stream(*args, **kwargs):
                yield b"\x00\x00\x00\x18ftypisom"
                yield b"\x00\x00\x00\x08free"

            mock_stream.side_effect = _fake_stream

            resp = self.client.get(f"/api/media/session/{self.session_id}/play.mp4")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers["Content-Type"], "video/mp4")
            self.assertIn("inline", resp.headers["Content-Disposition"])
            self.assertEqual(resp.content, b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x08free")

    def test_08_invalid_session_handling_404(self):
        """8. Verify 404 response for invalid or expired session ID on play.mp4 and player."""
        resp1 = self.client.get("/api/media/session/non-existent-session-id/play.mp4")
        self.assertEqual(resp1.status_code, 404)

        resp2 = self.client.get("/api/media/session/non-existent-session-id/player")
        self.assertEqual(resp2.status_code, 404)

    def test_09_ffmpeg_cleanup_on_cancellation(self):
        """9. Verify FFmpeg process and feeder resources are terminated on stream cancellation."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read.return_value = b"INITIAL_FMP4_BYTES"
        mock_proc.stderr = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch("app.services.media_probe.media_probe_service.probe_media", return_value=MagicMock(audio_codec="aac")):
                async def _test_cancel():
                    gen = self.remux.stream_fmp4(self.session)
                    chunk = await gen.__anext__()
                    self.assertEqual(chunk, b"INITIAL_FMP4_BYTES")
                    await gen.aclose()

                asyncio.run(_test_cancel())
                mock_proc.terminate.assert_called()

    def test_10_basic_progressive_output_behavior(self):
        """10. Verify progressive chunks are yielded as received without buffering full file."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout.read.side_effect = [
            b"CHUNK_1_FTYP_MOOV",
            b"CHUNK_2_MOOF_MDAT",
            b"",  # EOF
        ]
        mock_proc.stdin = MagicMock()
        mock_proc.stderr = MagicMock()

        async def _mock_stream_range(*args, **kwargs):
            yield b"\x00" * 1024
            yield b"\x01" * 1024

        with patch.object(self.session, "stream_byte_range", side_effect=_mock_stream_range):
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch("app.services.media_probe.media_probe_service.probe_media", return_value=MagicMock(audio_codec="aac")):
                    async def _collect():
                        chunks = []
                        async for chunk in self.remux.stream_fmp4(self.session):
                            chunks.append(chunk)
                        return chunks

                    result = asyncio.run(_collect())
                    self.assertEqual(result, [b"CHUNK_1_FTYP_MOOV", b"CHUNK_2_MOOF_MDAT"])

    def test_11_seeking_behavior_and_command_construction(self):
        """11. Verify seek parameter ?t=300 passes fast input seek -ss 300.000 to FFmpeg."""
        cmd = self.remux.build_remux_command(
            ffmpeg_bin="ffmpeg",
            seek_seconds=300.5,
            audio_codec="aac",
        )
        self.assertIn("-ss", cmd)
        idx = cmd.index("-ss")
        self.assertEqual(cmd[idx + 1], "300.500")

    def test_12_videojs_player_html_page(self):
        """12. Verify GET /api/media/session/{session_id}/player renders Video.js UI."""
        resp = self.client.get(f"/api/media/session/{self.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["Content-Type"])
        self.assertIn("video-js", resp.text)
        self.assertIn("cineforge-player", resp.text)
        self.assertIn(f"/api/media/session/{self.session_id}/play.mp4", resp.text)
        self.assertIn("/buffering", resp.text)

    def test_13_b6_range_streaming_regression(self):
        """13. Regression: Verify B6 RFC 7233 HTTP 206 Range streaming is unmodified."""
        resp = self.client.get(
            f"/api/media/stream/{self.session_id}",
            headers={"Range": "bytes=0-499"},
        )
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(resp.headers["Content-Range"], f"bytes 0-499/{self.file_size}")
        self.assertEqual(resp.headers["Content-Length"], "500")
        self.assertEqual(len(resp.content), 500)

    def test_14_b7_metadata_regression(self):
        """14. Regression: Verify B7 GET /api/media/session/{session_id}/metadata works."""
        resp = self.client.get(f"/api/media/session/{self.session_id}/metadata")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session_id)
        self.assertIn("metadata", data)
        self.assertIn("compatibility", data)

    def test_15_b8_buffering_metrics_regression(self):
        """15. Regression: Verify B8 GET /api/media/session/{session_id}/buffering works."""
        resp = self.client.get(f"/api/media/session/{self.session_id}/buffering")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session_id)
        self.assertIn("buffer_health", data)
        self.assertIn("download_throughput_bps", data)
        self.assertIn("prefetch_recommended", data)


if __name__ == "__main__":
    unittest.main()
