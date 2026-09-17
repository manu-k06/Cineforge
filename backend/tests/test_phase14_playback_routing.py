import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.services.stream_session import PlaybackSession, session_manager


class TestPhase14PlaybackRouting(unittest.TestCase):
    """Phase 14: Playback routing test suite asserting strictly automatic container-based routing with zero HLS."""

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        session_manager._sessions.clear()

    def test_01_mp4_routes_to_go_streamer(self):
        """Verify MP4 container routes automatically to native Go streamer redirect."""
        session = PlaybackSession(
            session_id="test-routing-mp4",
            chat_id="me",
            message_id=1001,
            file_name="Dune.Part.Two.2024.1080p.mp4",
            mime_type="video/mp4",
            file_size=2000000000,
            stream_url="http://127.0.0.1:8088/stream/me/1001?token=testtoken",
        )
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        body = resp.text

        # 1. Source must be Go streamer redirect
        self.assertIn(f'src="/api/media/stream/{session.session_id}"', body)
        self.assertIn('type="video/mp4"', body)
        self.assertIn("NATIVE BROWSER STREAM", body)
        self.assertIn("Direct Go streamer playback (MP4)", body)

        # 2. Must not contain progressive fMP4 as initial source
        self.assertNotIn(f'src="/api/media/session/{session.session_id}/play.mp4"', body)

        # 3. External player link must be direct Go streamer URL
        self.assertIn(f'href="{session.stream_url}"', body)

    def test_02_webm_routes_to_go_streamer(self):
        """Verify WebM container routes automatically to native Go streamer redirect with video/webm."""
        session = PlaybackSession(
            session_id="test-routing-webm",
            chat_id="me",
            message_id=1002,
            file_name="BigBuckBunny.webm",
            mime_type="video/webm",
            file_size=500000000,
            stream_url="http://127.0.0.1:8088/stream/me/1002?token=testtoken",
        )
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        body = resp.text

        # Source must be Go streamer redirect with video/webm
        self.assertIn(f'src="/api/media/stream/{session.session_id}"', body)
        self.assertIn('type="video/webm"', body)
        self.assertIn("NATIVE BROWSER STREAM", body)
        self.assertIn("Direct Go streamer playback (WEBM)", body)

    def test_03_mkv_routes_to_fmp4_remux(self):
        """Verify MKV container routes automatically to FFmpeg progressive fMP4 remux endpoint."""
        session = PlaybackSession(
            session_id="test-routing-mkv",
            chat_id="me",
            message_id=1003,
            file_name="Oppenheimer.2023.1080p.mkv",
            mime_type="video/x-matroska",
            file_size=3000000000,
            stream_url="http://127.0.0.1:8088/stream/me/1003?token=testtoken",
        )
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        body = resp.text

        # 1. Source must be progressive fMP4 remux
        self.assertIn(f'src="/api/media/session/{session.session_id}/play.mp4"', body)
        self.assertIn('type="video/mp4"', body)
        self.assertIn("PROGRESSIVE fMP4 REMUX", body)
        self.assertIn("Automatic stream-copy remux (MKV → fMP4)", body)

        # 2. Must NEVER feed raw MKV redirect to Video.js
        self.assertNotIn(f'src="/api/media/stream/{session.session_id}"', body)

        # 3. External player link still points directly to Go streamer URL
        self.assertIn(f'href="{session.stream_url}"', body)

    def test_04_incompatible_containers_route_to_fmp4_remux(self):
        """Verify other incompatible containers (AVI, TS) automatically route to progressive fMP4 remux."""
        for ext, mime in [("avi", "video/x-msvideo"), ("ts", "video/mp2t")]:
            sess_id = f"test-routing-{ext}"
            session = PlaybackSession(
                session_id=sess_id,
                chat_id="me",
                message_id=1004,
                file_name=f"Classic_Film.{ext}",
                mime_type=mime,
                file_size=1500000000,
                stream_url=f"http://127.0.0.1:8088/stream/me/1004?token=test_{ext}",
            )
            session_manager._sessions[sess_id] = session

            resp = self.client.get(f"/api/media/session/{sess_id}/player")
            self.assertEqual(resp.status_code, 200)
            body = resp.text

            self.assertIn(f'src="/api/media/session/{sess_id}/play.mp4"', body)
            self.assertIn("PROGRESSIVE fMP4 REMUX", body)
            self.assertIn(f"({ext.upper()} → fMP4)", body)

    def test_05_player_html_contains_no_hls_references(self):
        """Verify Player HTML contains zero HLS sources, zero m3u8 URLs, and zero HLS controls."""
        session = PlaybackSession(
            session_id="test-no-hls-inspection",
            chat_id="me",
            message_id=1005,
            file_name="Interstellar.2014.1080p.mkv",
            mime_type="video/x-matroska",
            file_size=2500000000,
            stream_url="http://127.0.0.1:8088/stream/me/1005",
        )
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        body = resp.text

        # Negative assertions: No HLS mime types or sources
        self.assertNotIn("application/x-mpegURL", body)
        self.assertNotIn("vnd.apple.mpegurl", body)
        self.assertNotIn(".m3u8", body)
        self.assertNotIn("master.m3u8", body)
        self.assertNotIn("index.m3u8", body)
        self.assertNotIn("hls.js", body)

        # No architecture switcher or mode toggle buttons
        self.assertNotIn("btn-mode-fmp4", body)
        self.assertNotIn("btn-mode-redirect", body)
        self.assertNotIn("btn-mode-hls", body)
        self.assertNotIn("switchMode", body)
        self.assertNotIn("HLS Mode", body)

    def test_06_obsolete_hls_endpoints_return_404(self):
        """Verify all former HLS endpoints return 404 Not Found."""
        session = PlaybackSession(
            session_id="test-obsolete-hls-404",
            chat_id="me",
            message_id=1006,
            file_name="Test.mkv",
            mime_type="video/x-matroska",
            file_size=10000000,
            stream_url="http://127.0.0.1:8088/stream/me/1006",
        )
        session_manager._sessions[session.session_id] = session

        endpoints = [
            f"/api/media/session/{session.session_id}/master.m3u8",
            f"/api/media/session/{session.session_id}/index.m3u8",
            f"/api/media/session/{session.session_id}/segment/0.mp4",
            f"/api/media/session/{session.session_id}/prebuffer",
        ]

        for ep in endpoints:
            resp = self.client.get(ep)
            self.assertEqual(
                resp.status_code,
                404,
                f"Endpoint '{ep}' should return 404 Not Found after complete HLS removal, got {resp.status_code}",
            )


if __name__ == "__main__":
    unittest.main()
