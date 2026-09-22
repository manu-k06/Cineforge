import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.subtitles import SubtitleTrack, SubtitleTrackListResponse
from app.services.subtitle_service import srt_to_vtt, subtitle_service


class TestSubtitleServiceAndEndpoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        subtitle_service._vtt_cache.clear()
        subtitle_service._tracks_cache.clear()

    def test_srt_to_vtt_conversion(self):
        """Verify SRT format is converted to compliant WebVTT format."""
        srt_input = (
            "1\r\n"
            "00:00:01,234 --> 00:00:04,567\r\n"
            "Look, the spinning top is still moving.\r\n\r\n"
            "2\r\n"
            "00:00:05,000 --> 00:00:08,000\r\n"
            "Is this reality or a dream?\r\n"
        )
        vtt = srt_to_vtt(srt_input)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.234 --> 00:00:04.567", vtt)
        self.assertIn("00:00:05.000 --> 00:00:08.000", vtt)
        self.assertIn("Look, the spinning top is still moving.", vtt)
        self.assertNotIn(",", vtt.split("-->")[0])

    def test_srt_to_vtt_empty_and_passthrough(self):
        """Verify empty strings and existing WebVTT content are handled safely."""
        self.assertEqual(srt_to_vtt(""), "WEBVTT\n\n")
        already_vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nHello"
        self.assertEqual(srt_to_vtt(already_vtt), already_vtt + "\n")

    def test_generate_demo_vtt(self):
        """Verify demo WebVTT contains movie title and valid cue blocks."""
        demo = subtitle_service.generate_demo_vtt("Interstellar")
        self.assertTrue(demo.startswith("WEBVTT"))
        self.assertIn("Interstellar", demo)
        self.assertIn("-->", demo)

    async def test_detect_embedded_subtitles_mocked(self):
        """Verify parsing of ffprobe JSON subtitle stream information."""
        mock_ffprobe_output = {
            "streams": [
                {
                    "index": 2,
                    "codec_name": "subrip",
                    "tags": {"language": "eng", "title": "English Full Dialogue"},
                    "disposition": {"default": 1},
                },
                {
                    "index": 3,
                    "codec_name": "ass",
                    "tags": {"language": "spa", "title": "Español Latino"},
                    "disposition": {"default": 0},
                },
            ]
        }

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            json.dumps(mock_ffprobe_output).encode("utf-8"),
            b"",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            tracks = await subtitle_service.detect_embedded_subtitles("https://media.stream/movie.mkv")

            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0].language, "en")
            self.assertEqual(tracks[0].label, "English Full Dialogue [Embedded]")
            self.assertEqual(tracks[0].codec, "subrip")
            self.assertTrue(tracks[0].is_default)
            self.assertIn("track_index=0", tracks[0].vtt_url)

            self.assertEqual(tracks[1].language, "es")
            self.assertEqual(tracks[1].label, "Español Latino [Embedded]")
            self.assertEqual(tracks[1].codec, "ass")
            self.assertFalse(tracks[1].is_default)

    async def test_extract_embedded_vtt_mocked_and_cached(self):
        """Verify ffmpeg subtitle extraction to WebVTT and subsequent in-memory cache hit."""
        mock_vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\nExtracted subtitle."

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (mock_vtt.encode("utf-8"), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            res1 = await subtitle_service.extract_embedded_vtt("https://media.stream/video.mp4", 0)
            self.assertEqual(res1, mock_vtt)
            self.assertEqual(mock_exec.call_count, 1)

            # Second request should be a cache hit with no subprocess call
            res2 = await subtitle_service.extract_embedded_vtt("https://media.stream/video.mp4", 0)
            self.assertEqual(res2, mock_vtt)
            self.assertEqual(mock_exec.call_count, 1)

    def test_api_get_tracks_endpoint(self):
        """GET /api/subtitles/tracks returns 200 with track list."""
        response = self.client.get(
            "/api/subtitles/tracks",
            params={"stream_url": "https://test.stream/video.mkv", "title": "Dune"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tracks", data)
        self.assertGreaterEqual(len(data["tracks"]), 1)
        self.assertEqual(data["tracks"][-1]["id"], "cineforge_demo_en")

    def test_api_demo_vtt_endpoint(self):
        """GET /api/subtitles/demo.vtt returns 200 with text/vtt content."""
        response = self.client.get("/api/subtitles/demo.vtt?title=Inception")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/vtt", response.headers.get("content-type", ""))
        self.assertTrue(response.text.startswith("WEBVTT"))
        self.assertIn("Inception", response.text)

    def test_api_embedded_vtt_endpoint(self):
        """GET /api/subtitles/embedded returns 200 with text/vtt media type."""
        with patch.object(
            subtitle_service,
            "extract_embedded_vtt",
            AsyncMock(return_value="WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nSub"),
        ):
            response = self.client.get(
                "/api/subtitles/embedded",
                params={"stream_url": "https://test.stream/video.mp4", "track_index": 0},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/vtt", response.headers.get("content-type", ""))
            self.assertTrue(response.text.startswith("WEBVTT"))
