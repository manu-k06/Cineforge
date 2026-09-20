import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.telegram import telegram_service


class TestStreamerBotIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_extract_streamer_links_from_screenshot_format(self):
        """Verify _extract_streamer_links correctly extracts stream, watch, and download URLs from @stre89d_bot format."""
        mock_msg = MagicMock()
        mock_msg.message = "https://app-engine-rbtn.onrender.com/stream/27?hash=03afc8"

        # Mock inline keyboard buttons
        btn_watch = MagicMock()
        btn_watch.text = "▶ Watch Online"
        btn_watch.url = "https://app-engine-rbtn.onrender.com/watch/27?hash=03afc8"

        btn_download = MagicMock()
        btn_download.text = "⬇ Download"
        btn_download.url = "https://app-engine-rbtn.onrender.com/download/27?hash=03afc8"

        btn_stream = MagicMock()
        btn_stream.text = "⚡ Stream Link"
        btn_stream.url = "https://app-engine-rbtn.onrender.com/stream/27?hash=03afc8"

        mock_msg.buttons = [
            [btn_watch, btn_download],
            [btn_stream],
        ]

        links = telegram_service._extract_streamer_links(mock_msg)
        self.assertEqual(links["stream_url"], "https://app-engine-rbtn.onrender.com/stream/27?hash=03afc8")
        self.assertEqual(links["watch_url"], "https://app-engine-rbtn.onrender.com/watch/27?hash=03afc8")
        self.assertEqual(links["download_url"], "https://app-engine-rbtn.onrender.com/download/27?hash=03afc8")

    def test_mock_deliver_candidate_response(self):
        """Verify POST /api/search/deliver returns valid stream and player URLs."""
        payload = {
            "candidate_id": "mock_mp4_1080",
            "source_bot": "Spoty_xbot",
            "start_payload": "mock_payload",
        }
        resp = self.client.post("/api/search/deliver", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("stream_url", data)
        self.assertIn("watch_url", data)
        self.assertTrue(data["stream_url"].startswith("https://app-engine-rbtn.onrender.com/stream"))
        self.assertTrue(data["watch_url"].startswith("https://app-engine-rbtn.onrender.com/watch"))


if __name__ == "__main__":
    unittest.main()
