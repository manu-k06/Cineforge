import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.probe import SubtitleTrackInfo
from app.services.stream_session import PlaybackSession, session_manager
from app.services.subtitle_service import subtitle_service


class TestPhase16Subtitles(unittest.TestCase):
    """Phase 16: Embedded subtitle extraction, WebVTT streaming, and player UI controls."""

    def setUp(self):
        self.client = TestClient(app)
        subtitle_service._vtt_cache.clear()

    def tearDown(self):
        session_manager._sessions.clear()
        subtitle_service._vtt_cache.clear()

    def test_01_subtitle_track_model(self):
        """Verify SubtitleTrackInfo structure and defaults."""
        track = SubtitleTrackInfo(
            track_id=0,
            stream_index=2,
            codec="subrip",
            is_text=True,
            language="eng",
            title="English [SDH]",
            vtt_url="/api/media/session/test-sess/subtitles/0.vtt",
        )
        self.assertEqual(track.track_id, 0)
        self.assertEqual(track.stream_index, 2)
        self.assertEqual(track.codec, "subrip")
        self.assertTrue(track.is_text)
        self.assertEqual(track.language, "eng")
        self.assertEqual(track.title, "English [SDH]")

    def test_02_get_subtitles_endpoint(self):
        """Verify GET /api/media/session/{session_id}/subtitles returns track list."""
        session = PlaybackSession(
            session_id="test-sub-session",
            chat_id="me",
            message_id=5555,
            file_name="Inception.2010.1080p.mkv",
            mime_type="video/x-matroska",
            file_size=1500000000,
            stream_url="http://127.0.0.1:8088/stream/me/5555?token=subtok",
        )
        session._cached_subtitle_tracks = [
            SubtitleTrackInfo(
                track_id=0,
                stream_index=2,
                codec="subrip",
                is_text=True,
                language="eng",
                title="English [SDH]",
                vtt_url=f"/api/media/session/{session.session_id}/subtitles/0.vtt",
            ),
            SubtitleTrackInfo(
                track_id=1,
                stream_index=3,
                codec="subrip",
                is_text=True,
                language="spa",
                title="Spanish",
                vtt_url=f"/api/media/session/{session.session_id}/subtitles/1.vtt",
            ),
        ]
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/subtitles")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["language"], "eng")
        self.assertEqual(data[0]["title"], "English [SDH]")
        self.assertEqual(data[1]["language"], "spa")
        self.assertEqual(data[1]["track_id"], 1)

    def test_03_extract_vtt_endpoint(self):
        """Verify GET /api/media/session/{session_id}/subtitles/{track_id}.vtt returns WebVTT."""
        session = PlaybackSession(
            session_id="test-vtt-extract",
            chat_id="me",
            message_id=6666,
            file_name="Movie.mkv",
            mime_type="video/x-matroska",
            file_size=1200000000,
            stream_url="http://127.0.0.1:8088/stream/me/6666?token=vtttok",
        )
        session_manager._sessions[session.session_id] = session

        # Mock extract_vtt to return simulated WebVTT text
        mock_vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nHello world!"
        with patch.object(subtitle_service, "extract_vtt", new=AsyncMock(return_value=mock_vtt)):
            resp = self.client.get(f"/api/media/session/{session.session_id}/subtitles/0.vtt")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.headers["content-type"].startswith("text/vtt"))
            self.assertIn("WEBVTT", resp.text)
            self.assertIn("Hello world!", resp.text)

    def test_04_vtt_in_memory_caching(self):
        """Verify that extracted VTT is cached in memory for zero-latency subsequent requests."""
        session = PlaybackSession(
            session_id="test-cache-sess",
            chat_id="me",
            message_id=7777,
            file_name="Cached.mkv",
            mime_type="video/x-matroska",
            file_size=1000000000,
            stream_url="http://127.0.0.1:8088/stream/me/7777?token=cachetok",
        )
        session_manager._sessions[session.session_id] = session

        cache_key = f"{session.session_id}:0"
        mock_vtt = "WEBVTT\n\n1\n00:00:02.000 --> 00:00:05.000\nCached subtitle"
        subtitle_service._vtt_cache[cache_key] = mock_vtt

        resp = self.client.get(f"/api/media/session/{session.session_id}/subtitles/0.vtt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, mock_vtt)

    def test_05_player_ui_renders_subtitles_and_controls(self):
        """Verify player HTML includes <track> tags, file upload button, and sync controls."""
        session = PlaybackSession(
            session_id="test-player-ui",
            chat_id="me",
            message_id=8888,
            file_name="Avatar.2009.1080p.mkv",
            mime_type="video/x-matroska",
            file_size=2500000000,
            stream_url="http://127.0.0.1:8088/stream/me/8888?token=avatok",
        )
        session._cached_subtitle_tracks = [
            SubtitleTrackInfo(
                track_id=0,
                stream_index=2,
                codec="subrip",
                is_text=True,
                language="eng",
                title="English [SDH]",
                vtt_url=f"/api/media/session/{session.session_id}/subtitles/0.vtt",
            )
        ]
        session_manager._sessions[session.session_id] = session

        resp = self.client.get(f"/api/media/session/{session.session_id}/player")
        self.assertEqual(resp.status_code, 200)
        body = resp.text

        # 1. HTML <track> element must be injected
        self.assertIn('<track kind="subtitles"', body)
        self.assertIn(f'/api/media/session/{session.session_id}/subtitles/0.vtt', body)
        self.assertIn('label="English [SDH]"', body)

        # 2. Local file upload controls must be present
        self.assertIn('Load Subtitle (.srt / .vtt)', body)
        self.assertIn('id="sub-file-input"', body)
        self.assertIn('id="sub-active-badge"', body)

        # 3. Subtitle timing sync controls must be present
        self.assertIn('Sync Offset:', body)
        self.assertIn('adjustSubOffset(-0.5)', body)
        self.assertIn('adjustSubOffset(0.5)', body)
        self.assertIn('id="sub-offset-val"', body)

        # 4. Client-side JS functions must be present
        self.assertIn('function srtToVtt(', body)
        self.assertIn('function loadSubtitleFile(', body)
        self.assertIn('function adjustSubOffset(', body)


if __name__ == "__main__":
    unittest.main()
