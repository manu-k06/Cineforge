import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.models.search import SearchResultItem, ButtonInfo
from app.services.compatibility import (
    MediaCompatibilityResult,
    MediaCompatibilityService,
    compatibility_service,
)


class TestPhase14MediaCompatibility(unittest.TestCase):
    def setUp(self):
        self.service = MediaCompatibilityService()
        self.client = TestClient(app)

    def test_01_mime_type_detection(self):
        """Verify browser playability is properly classified via MIME types."""
        # MP4
        res = self.service.get_media_compatibility(mime_type="video/mp4")
        self.assertTrue(res.browser_playable)
        self.assertEqual(res.container, "mp4")
        self.assertEqual(res.playback_mode, "browser")

        # WebM
        res = self.service.get_media_compatibility(mime_type="video/webm")
        self.assertTrue(res.browser_playable)
        self.assertEqual(res.container, "webm")
        self.assertEqual(res.playback_mode, "browser")

        # MKV
        res = self.service.get_media_compatibility(mime_type="video/x-matroska")
        self.assertFalse(res.browser_playable)
        self.assertEqual(res.container, "mkv")
        self.assertEqual(res.playback_mode, "external")

        # AVI
        res = self.service.get_media_compatibility(mime_type="video/x-msvideo")
        self.assertFalse(res.browser_playable)
        self.assertEqual(res.container, "avi")
        self.assertEqual(res.playback_mode, "external")

    def test_02_filename_extension_fallback(self):
        """Verify extension fallback when MIME type is generic or missing."""
        # Generic octet-stream with .mp4
        res = self.service.get_media_compatibility(
            filename="Avatar.2009.1080p.BluRay.mp4",
            mime_type="application/octet-stream",
        )
        self.assertTrue(res.browser_playable)
        self.assertEqual(res.container, "mp4")
        self.assertEqual(res.playback_mode, "browser")

        # Generic octet-stream with .mkv
        res = self.service.get_media_compatibility(
            filename="Avatar.2009.1080p.BluRay.mkv",
            mime_type="application/octet-stream",
        )
        self.assertFalse(res.browser_playable)
        self.assertEqual(res.container, "mkv")
        self.assertEqual(res.playback_mode, "external")

        # Missing MIME type with .webm
        res = self.service.get_media_compatibility(filename="clip.webm")
        self.assertTrue(res.browser_playable)
        self.assertEqual(res.container, "webm")
        self.assertEqual(res.playback_mode, "browser")

    def test_03_substring_false_positive_prevention(self):
        """Verify filenames with embedded misleading substrings are correctly parsed by actual container extension."""
        # A file named Movie.mp4.rip.mkv is an MKV, not an MP4
        res = self.service.get_media_compatibility(filename="Inception.mp4.rip.1080p.mkv")
        self.assertFalse(res.browser_playable)
        self.assertEqual(res.container, "mkv")
        self.assertEqual(res.playback_mode, "external")

        # A file named Movie.mkv.converted.mp4 is an MP4, not an MKV
        res = self.service.get_media_compatibility(filename="Inception.mkv.converted.mp4")
        self.assertTrue(res.browser_playable)
        self.assertEqual(res.container, "mp4")
        self.assertEqual(res.playback_mode, "browser")

    def test_04_search_ranking_prioritization(self):
        """Verify candidate ranking: MP4 1080p > MP4 720p > MKV 1080p > MKV 720p."""
        items = [
            SearchResultItem(
                message_id=1,
                text="Interstellar 1080p BluRay.mkv (2.1 GB)",
                browser_playable=False,
                container="mkv",
                playback_mode="external",
            ),
            SearchResultItem(
                message_id=2,
                text="Interstellar 1080p WEB-DL.mp4 (1.9 GB)",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
            ),
            SearchResultItem(
                message_id=3,
                text="Interstellar 720p HD.mkv (1.1 GB)",
                browser_playable=False,
                container="mkv",
                playback_mode="external",
            ),
            SearchResultItem(
                message_id=4,
                text="Interstellar 720p HD.mp4 (1.0 GB)",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
            ),
        ]

        ranked = self.service.rank_search_results(items)
        ranked_ids = [item.message_id for item in ranked]

        # Expected order: message_id 2 (MP4 1080p), 4 (MP4 720p), 1 (MKV 1080p), 3 (MKV 720p)
        self.assertEqual(ranked_ids, [2, 4, 1, 3])
        self.assertTrue(ranked[0].browser_playable)
        self.assertTrue(ranked[1].browser_playable)
        self.assertFalse(ranked[2].browser_playable)
        self.assertFalse(ranked[3].browser_playable)

    def test_05_mock_search_endpoint(self):
        """Verify GET /api/search?mock=true returns ranked items with compatibility metadata."""
        resp = self.client.get("/api/search?query=Inception&mock=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["query"], "Inception")
        self.assertEqual(len(data["results"]), 4)

        results = data["results"]
        self.assertEqual(len(results), 4)

        # Result 0 must be MP4 1080p
        self.assertEqual(results[0]["container"], "mp4")
        self.assertTrue(results[0]["browser_playable"])
        self.assertEqual(results[0]["playback_mode"], "browser")

        # Result 1 must be MP4 720p
        self.assertEqual(results[1]["container"], "mp4")
        self.assertTrue(results[1]["browser_playable"])

        # Result 2 must be MKV 1080p
        self.assertEqual(results[2]["container"], "mkv")
        self.assertFalse(results[2]["browser_playable"])
        self.assertEqual(results[2]["playback_mode"], "external")

        # Result 3 must be MKV 720p
        self.assertEqual(results[3]["container"], "mkv")
        self.assertFalse(results[3]["browser_playable"])

    def test_06_search_ui_endpoint(self):
        """Verify GET /api/search/ui renders the search interface with compatibility cues."""
        resp = self.client.get("/api/search/ui")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        body = resp.text
        self.assertIn("CineForge Search", body)
        self.assertIn("Browser Playable", body)
        self.assertIn("External Player", body)
        self.assertIn("/api/media/session", body)

    def test_07_root_redirect(self):
        """Verify GET / redirects to /api/search/ui."""
        resp = self.client.get("/", follow_redirects=False)
        self.assertEqual(resp.status_code, 307)
        self.assertEqual(resp.headers.get("location"), "/api/search/ui")


if __name__ == "__main__":
    unittest.main()
