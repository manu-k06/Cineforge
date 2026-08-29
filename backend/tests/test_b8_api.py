import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.buffering import BufferHealthState, SessionBufferingMetrics
from app.services.stream_session import MediaStreamSession, session_manager


class TestMilestoneB8APIAndRegressions(unittest.TestCase):
    """Test suite for Milestone B8 API endpoints and B6/B7 regressions."""

    def setUp(self):
        self.client = TestClient(app)
        self.file_size = 1125702788
        self.bitrate = 1013226

        # Create a mock reader
        mock_reader = MagicMock()
        mock_reader.get_file_size.return_value = self.file_size
        mock_reader.get_mime_type.return_value = "video/x-matroska"
        mock_reader.get_file_name.return_value = "Inception.mkv"
        mock_reader.get_video_metadata.return_value = MagicMock(duration_seconds=8888.06)
        mock_reader.read_range = AsyncMock(return_value=b"\x00" * 524288)

        # Create and register a real session
        self.session_id = "test-b8-api-session"
        self.session = MediaStreamSession(
            session_id=self.session_id,
            reader=mock_reader,
            max_buffer_mb=16,
        )
        self.session.cache.put(0, b"\x00" * 524288)
        self.session.cache.put(1, b"\x01" * 524288)
        self.session.throughput_estimator.record_sample(1048576, 8.0)
        session_manager._sessions[self.session_id] = self.session

    def tearDown(self):
        session_manager._sessions.pop(self.session_id, None)

    def test_01_get_buffering_metrics_endpoint(self):
        """Verify GET /api/media/session/{session_id}/buffering endpoint returns valid B8 metrics."""
        resp = self.client.get(f"/api/media/session/{self.session_id}/buffering")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session_id)
        self.assertEqual(data["buffered_bytes"], 1048576)
        self.assertAlmostEqual(data["buffered_seconds"], 8.28, delta=0.5)
        self.assertIn("buffer_health", data)
        self.assertIn("prefetch_recommended", data)
        self.assertIn("prefetch_action", data)
        self.assertIn("recommended_prefetch_chunks", data)

    def test_02_buffering_nonexistent_session_404(self):
        """Verify 404 response for invalid/expired session."""
        resp = self.client.get("/api/media/session/nonexistent-session-id/buffering")
        self.assertEqual(resp.status_code, 404)

    def test_03_b6_range_streaming_regression(self):
        """Verify B6 RFC 7233 HTTP 206 Range streaming still works perfectly."""
        # Request first 1000 bytes
        resp = self.client.get(
            f"/api/media/stream/{self.session_id}",
            headers={"Range": "bytes=0-999"},
        )
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(resp.headers["Content-Range"], f"bytes 0-999/{self.file_size}")
        self.assertEqual(resp.headers["Content-Length"], "1000")
        self.assertEqual(resp.headers["Accept-Ranges"], "bytes")
        self.assertEqual(len(resp.content), 1000)

    def test_04_b6_invalid_range_416_regression(self):
        """Verify B6 416 Range Not Satisfiable on out-of-bounds range."""
        resp = self.client.get(
            f"/api/media/stream/{self.session_id}",
            headers={"Range": "bytes=2000000000-2000010000"},
        )
        self.assertEqual(resp.status_code, 416)
        self.assertIn(f"bytes */{self.file_size}", resp.headers.get("Content-Range", ""))

    def test_05_b7_metadata_endpoint_regression(self):
        """Verify B7 GET /api/media/session/{session_id}/metadata endpoint still works."""
        resp = self.client.get(f"/api/media/session/{self.session_id}/metadata")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session_id)
        self.assertIn("metadata", data)
        self.assertIn("compatibility", data)
        self.assertIn("sustainability", data)
        self.assertIn("buffer", data)


if __name__ == "__main__":
    unittest.main()
