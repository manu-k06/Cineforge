import hashlib
import hmac
import time
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.stream_session import (
    PlaybackSession,
    generate_stream_url,
    session_manager,
)


class TestPhase11StreamIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear active sessions before each test
        session_manager._sessions.clear()

    def tearDown(self):
        session_manager._sessions.clear()

    def test_01_create_playback_session_default_chat(self):
        """Verify POST /api/stream/session creates lightweight session with default chat='me'."""
        response = self.client.post("/api/stream/session", json={"message_id": 9763})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertEqual(data["chat_id"], "me")
        self.assertEqual(data["message_id"], 9763)
        self.assertTrue(data["stream_url"].startswith(f"{settings.STREAMER_BASE_URL}/stream/me/9763"))
        self.assertGreater(data["expires_at"], data["created_at"])

        # Also check session stored in session_manager
        session = session_manager._sessions.get(data["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session.chat_id, "me")
        self.assertEqual(session.message_id, 9763)

    def test_02_create_playback_session_custom_chat(self):
        """Verify POST /api/media/session supports numeric or string chat IDs."""
        response = self.client.post(
            "/api/media/session",
            json={"chat_id": "cineforge_channel", "message_id": 1234},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["chat_id"], "cineforge_channel")
        self.assertEqual(data["message_id"], 1234)
        self.assertTrue(data["stream_url"].startswith(f"{settings.STREAMER_BASE_URL}/stream/cineforge_channel/1234"))

    def test_03_missing_or_invalid_message_id(self):
        """Verify 400 or 422 error on missing or invalid message_id."""
        resp1 = self.client.post("/api/stream/session", json={"chat_id": "me"})
        self.assertEqual(resp1.status_code, 422)  # Missing required field

        resp2 = self.client.post("/api/stream/session", json={"message_id": -5})
        self.assertEqual(resp2.status_code, 400)  # Invalid message ID

        resp3 = self.client.post("/api/stream/session", json={"message_id": 0})
        self.assertEqual(resp3.status_code, 400)  # Invalid message ID

    def test_04_stream_url_generation_without_secret(self):
        """Verify stream URL contains no HMAC query params when STREAM_SECRET_KEY is empty."""
        with patch.object(settings, "STREAM_SECRET_KEY", ""):
            url = generate_stream_url("me", 9763, expires_at=1800000000)
            self.assertEqual(url, f"{settings.STREAMER_BASE_URL}/stream/me/9763")

    def test_05_stream_url_generation_with_hmac_secret(self):
        """Verify signed stream URL matches streamer/auth.go HMAC-SHA256 algorithm exactly."""
        test_secret = "cineforge_super_secret_stream_key_42"
        exp_ts = 1800000000
        chat_id = "me"
        msg_id = 9763

        with patch.object(settings, "STREAM_SECRET_KEY", test_secret):
            url = generate_stream_url(chat_id, msg_id, expires_at=exp_ts)
            expected_prefix = f"{settings.STREAMER_BASE_URL}/stream/{chat_id}/{msg_id}?exp={exp_ts}&sig="
            self.assertTrue(url.startswith(expected_prefix))

            # Compute expected HMAC signature per streamer/auth.go
            expected_message = f"{chat_id}:{msg_id}:{exp_ts}"
            expected_sig = hmac.new(
                test_secret.encode("utf-8"),
                expected_message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            actual_sig = url.split("&sig=")[1]
            self.assertEqual(actual_sig, expected_sig)

    def test_06_get_session_details(self):
        """Verify GET /api/stream/session/{session_id} returns session details."""
        resp = self.client.post("/api/stream/session", json={"message_id": 9763})
        session_id = resp.json()["session_id"]

        detail_resp = self.client.get(f"/api/stream/session/{session_id}")
        self.assertEqual(detail_resp.status_code, 200)
        data = detail_resp.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["chat_id"], "me")
        self.assertEqual(data["message_id"], 9763)
        self.assertFalse(data["is_expired"])

    def test_07_invalid_and_expired_session_lookup(self):
        """Verify 404 for non-existent session and expired session handling."""
        # Non-existent
        resp = self.client.get("/api/stream/session/non-existent-uuid")
        self.assertEqual(resp.status_code, 404)

        # Expired session
        expired_session = PlaybackSession(
            session_id="expired-session-uuid",
            chat_id="me",
            message_id=9763,
            stream_url="http://127.0.0.1:8088/stream/me/9763",
            created_at=time.time() - 3600,
            expires_at=time.time() - 100,  # Expired in past
        )
        session_manager._sessions["expired-session-uuid"] = expired_session

        # Accessing /session/expired-session-uuid or /stream/expired-session-uuid
        stream_resp = self.client.get("/api/media/stream/expired-session-uuid", follow_redirects=False)
        self.assertIn(stream_resp.status_code, [404, 410])

    def test_08_delete_session(self):
        """Verify DELETE /api/stream/session/{session_id} removes session."""
        resp = self.client.post("/api/stream/session", json={"message_id": 9763})
        session_id = resp.json()["session_id"]

        del_resp = self.client.delete(f"/api/stream/session/{session_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertNotIn(session_id, session_manager._sessions)

        # Subsequent lookup returns 404
        self.assertEqual(self.client.get(f"/api/stream/session/{session_id}").status_code, 404)

    def test_09_stream_media_serves_bytes_directly(self):
        """Verify GET /api/media/stream/{session_id} serves bytes directly as HTTP 206 Partial Content.

        The Go streamer redirect (307) was removed because the Go streamer is unreliable
        and caused playback failures (DC auth errors, wrong-DC errors). PlaybackSessions
        now stream bytes directly via Python MTProto for all range requests.
        """
        import uuid
        # Create a PlaybackSession with a known file_size so the Range request is valid
        session_id = str(uuid.uuid4())
        session = PlaybackSession(
            session_id=session_id,
            chat_id="me",
            message_id=9763,
            stream_url=generate_stream_url("me", 9763),
            file_name="test_movie.mp4",
            mime_type="video/mp4",
            file_size=10 * 1024 * 1024,  # 10 MB
        )
        # Register directly (tests are single-threaded, no lock needed)
        session_manager._sessions[session_id] = session

        stream_resp = self.client.get(
            f"/api/media/stream/{session_id}",
            follow_redirects=False,
            headers={"Range": "bytes=0-1023"},
        )
        self.assertEqual(stream_resp.status_code, 206)
        self.assertIn("Content-Range", stream_resp.headers)
        self.assertIn("Accept-Ranges", stream_resp.headers)
        self.assertEqual(stream_resp.headers["Accept-Ranges"], "bytes")

    @patch("httpx.AsyncClient.get")
    def test_10_streamer_health_healthy(self, mock_get):
        """Verify /streamer/health reports healthy when Go streamer returns 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "cineforge-streamer",
            "engine": "gotd/td",
        }
        mock_get.return_value = mock_response

        resp = self.client.get("/api/stream/streamer/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["reachable"])
        self.assertEqual(data["details"]["service"], "cineforge-streamer")

    @patch("httpx.AsyncClient.get")
    def test_11_streamer_health_unreachable(self, mock_get):
        """Verify /streamer/health reports unreachable when Go streamer fails."""
        mock_get.side_effect = Exception("Connection refused to 127.0.0.1:8088")

        resp = self.client.get("/api/media/streamer/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "unreachable")
        self.assertFalse(data["reachable"])
        self.assertIn("Connection refused", data["error"])


if __name__ == "__main__":
    unittest.main()
