import gzip
import io
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
            "<font color=\"#ffff00\">Look, the spinning top is still moving.</font>\r\n\r\n"
            "2\r\n"
            "00:00:05,000 --> 00:00:08,000\r\n"
            "Is this reality or a dream?\r\n"
        )
        vtt = srt_to_vtt(srt_input)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.234 --> 00:00:04.567", vtt)
        self.assertIn("00:00:05.000 --> 00:00:08.000", vtt)
        self.assertIn("Look, the spinning top is still moving.", vtt)
        self.assertNotIn("<font", vtt)
        self.assertNotIn(",", vtt.split("-->")[0])

    def test_srt_to_vtt_bom_and_empty(self):
        """Verify BOM stripping and empty content handling."""
        self.assertEqual(srt_to_vtt(""), "WEBVTT\n\n")
        bom_srt = "\ufeff1\n00:00:01,000 --> 00:00:02,000\nHello World\n"
        vtt = srt_to_vtt(bom_srt)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:02.000", vtt)

    def test_generate_demo_vtt(self):
        """Verify demo WebVTT contains movie title and valid cue blocks."""
        demo = subtitle_service.generate_demo_vtt("Interstellar")
        self.assertTrue(demo.startswith("WEBVTT"))
        self.assertIn("Interstellar", demo)
        self.assertIn("-->", demo)

    async def test_search_opensubtitles_mocked(self):
        """Verify parsing of OpenSubtitles REST JSON and deduplication."""
        mock_api_data = [
            {
                "SubLanguageID": "eng",
                "ISO639": "en",
                "LanguageName": "English",
                "SubRating": "8.5",
                "SubDownloadsCnt": 12000,
                "IDSubtitleFile": 1952382,
                "SubDownloadLink": "https://dl.opensubtitles.org/sub/1952382.gz",
            },
            {
                "SubLanguageID": "spa",
                "ISO639": "es",
                "LanguageName": "Spanish",
                "SubRating": "7.9",
                "SubDownloadsCnt": 5000,
                "IDSubtitleFile": 1952383,
                "SubDownloadLink": "https://dl.opensubtitles.org/sub/1952383.gz",
            },
        ]

        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_api_data

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_res)):
            tracks = await subtitle_service.search_opensubtitles(
                imdb_id="tt1375666",
                title="Inception",
            )
            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0].language, "en")
            self.assertEqual(tracks[0].label, "English")
            self.assertEqual(tracks[0].provider, "opensubtitles")
            self.assertTrue(tracks[0].is_default)
            self.assertIn("/api/subtitles/vtt?source=opensubtitles", tracks[0].vtt_url)

            self.assertEqual(tracks[1].language, "es")
            self.assertEqual(tracks[1].label, "Spanish")
            self.assertFalse(tracks[1].is_default)

    async def test_search_stremio_opensubtitles_mocked(self):
        """Verify parsing of Stremio OpenSubtitles v3 CDN JSON and deduplication."""
        mock_api_data = {
            "subtitles": [
                {
                    "id": "1001",
                    "lang": "eng",
                    "url": "https://subs5.strem.io/en/1001",
                },
                {
                    "id": "1002",
                    "lang": "spa",
                    "url": "https://subs5.strem.io/es/1002",
                },
                {
                    "id": "1003",
                    "lang": "eng",
                    "url": "https://subs5.strem.io/en/1003",  # duplicate lang
                },
            ]
        }

        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_api_data

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_res)):
            tracks = await subtitle_service.search_stremio_opensubtitles(
                imdb_id="tt1979388",
                title="The Good Dinosaur",
            )
            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0].language, "en")
            self.assertEqual(tracks[0].label, "English")
            self.assertEqual(tracks[0].provider, "opensubtitles")
            self.assertTrue(tracks[0].is_default)
            self.assertIn("source=stremio", tracks[0].vtt_url)

            self.assertEqual(tracks[1].language, "es")
            self.assertEqual(tracks[1].label, "Spanish")
            self.assertFalse(tracks[1].is_default)

    async def test_download_and_convert_vtt_stremio_utf8(self):
        """Verify direct UTF-8 SRT download from Stremio CDN and conversion to WebVTT."""
        raw_srt = "1\n00:01:00,000 --> 00:01:05,000\nHello from Stremio CDN!"
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = raw_srt.encode("utf-8")
        mock_res.text = raw_srt

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_res)):
            vtt = await subtitle_service.download_and_convert_vtt(
                source="stremio",
                download_url="https://subs5.strem.io/file.srt",
                sub_id="1001",
                title="The Good Dinosaur",
            )
            self.assertTrue(vtt.startswith("WEBVTT"))
            self.assertIn("00:01:00.000 --> 00:01:05.000", vtt)
            self.assertIn("Hello from Stremio CDN!", vtt)

    async def test_download_and_convert_vtt_gzip_cached(self):
        """Verify OpenSubtitles gzip decompression, conversion, and in-memory caching."""
        raw_srt = "1\n00:00:01,000 --> 00:00:03,000\nSub dialogue line."
        gz_bytes = gzip.compress(raw_srt.encode("utf-8"))

        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = gz_bytes

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_res)) as mock_get:
            vtt1 = await subtitle_service.download_and_convert_vtt(
                source="opensubtitles",
                download_url="https://dl.opensubtitles.org/file.gz",
                sub_id="123",
                title="Test Movie",
            )
            self.assertTrue(vtt1.startswith("WEBVTT"))
            self.assertIn("Sub dialogue line.", vtt1)
            self.assertEqual(mock_get.call_count, 1)

            # Second request should be served from memory cache without network call
            vtt2 = await subtitle_service.download_and_convert_vtt(
                source="opensubtitles",
                download_url="https://dl.opensubtitles.org/file.gz",
                sub_id="123",
                title="Test Movie",
                )
            self.assertEqual(vtt1, vtt2)
            self.assertEqual(mock_get.call_count, 1)

    def test_api_get_tracks_endpoint(self):
        """GET /api/subtitles/tracks returns 200 with track list and demo fallback."""
        response = self.client.get(
            "/api/subtitles/tracks",
            params={"title": "Dune", "year": 2021},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tracks", data)
        self.assertGreaterEqual(len(data["tracks"]), 1)
        # Verify Cineforge Sync track is present
        self.assertEqual(data["tracks"][-1]["id"], "cineforge_demo_en")
        self.assertEqual(data["tracks"][-1]["provider"], "sync")

    def test_api_vtt_stream_endpoint(self):
        """GET /api/subtitles/vtt returns 200 with text/vtt media type."""
        with patch.object(
            subtitle_service,
            "download_and_convert_vtt",
            AsyncMock(return_value="WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nSub"),
        ):
            response = self.client.get(
                "/api/subtitles/vtt",
                params={"source": "opensubtitles", "download_url": "https://test.dl/1.gz", "lang": "en"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/vtt", response.headers.get("content-type", ""))
            self.assertTrue(response.text.startswith("WEBVTT"))

    def test_api_demo_vtt_endpoint(self):
        """GET /api/subtitles/demo.vtt returns 200 with text/vtt content."""
        response = self.client.get("/api/subtitles/demo.vtt?title=Inception")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/vtt", response.headers.get("content-type", ""))
        self.assertTrue(response.text.startswith("WEBVTT"))
        self.assertIn("Inception", response.text)
