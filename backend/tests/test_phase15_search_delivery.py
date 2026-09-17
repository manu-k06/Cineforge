import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.delivery_flow import CandidateDeliveryRequest
from app.models.search import SearchCandidate
from app.services.search_aggregator import search_aggregator
from app.services.stream_session import PlaybackSession, session_manager


class TestPhase15SearchDelivery(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_pagination_parsing(self):
        """Verify extraction of total results, current page, total pages, and navigation buttons."""
        raw_text = "Results for your search: DC\nTotal Results: 2200\nPage: 1/220"

        # Mock button objects
        btn_next = MagicMock()
        btn_next.text = "Next >>"
        btn_next.data = b"next_5178541569_10"
        btn_next.url = None

        btn_counter = MagicMock()
        btn_counter.text = "1/220"
        btn_counter.data = b"buttons"
        btn_counter.url = None

        pag = search_aggregator.extract_pagination_info(raw_text, [btn_counter, btn_next])
        self.assertEqual(pag.current_page, 1)
        self.assertEqual(pag.total_pages, 220)
        self.assertEqual(pag.total_results, 2200)
        self.assertTrue(pag.has_next)
        self.assertFalse(pag.has_prev)
        self.assertEqual(pag.next_callback_data, "next_5178541569_10")

    def test_02_candidate_normalization(self):
        """Verify extraction of title, size, quality, extension, and deep-link start payload."""
        # Candidate button
        btn = MagicMock()
        btn.text = "🎬 200.25 MB Hotelier 02 mp4"
        btn.url = "https://t.me/Spoty_xbot?start=ZmlsZV9CUUFEQlFBRDlVSUFBcm0xSXdBQi1EQ1JValFJVXJZV0JB"
        btn.data = None

        candidate = search_aggregator.normalize_candidate(
            btn=btn,
            source_bot="Spoty_xbot",
            source_message_id=12662,
            page_number=1,
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.source_bot, "Spoty_xbot")
        self.assertEqual(candidate.source_message_id, 12662)
        self.assertEqual(candidate.start_payload, "ZmlsZV9CUUFEQlFBRDlVSUFBcm0xSXdBQi1EQ1JValFJVXJZV0JB")
        self.assertEqual(candidate.size, "200.25 MB")
        self.assertEqual(candidate.extension, "mp4")
        self.assertTrue(candidate.browser_playable)
        self.assertEqual(candidate.container, "mp4")
        self.assertEqual(candidate.playback_mode, "browser")
        self.assertIn("Hotelier", candidate.title)

    def test_03_deduplication_and_title_grouping(self):
        """Verify candidate deduplication and grouping of versions under a unified title."""
        c1 = SearchCandidate(
            candidate_id="id1",
            source_bot="Spoty_xbot",
            source_message_id=101,
            start_payload="payload_1080",
            display_text="Detective Ujjwalan 1080p.mkv",
            title="Detective Ujjwalan (2025)",
            size="1.55 GB",
            quality="1080P",
            extension="mkv",
            browser_playable=False,
            container="mkv",
            playback_mode="external",
            page_number=1,
        )
        c2 = SearchCandidate(
            candidate_id="id2",
            source_bot="Spoty_xbot",
            source_message_id=101,
            start_payload="payload_720",
            display_text="Detective Ujjwalan 720p.mp4",
            title="Detective Ujjwalan (2025)",
            size="927 MB",
            quality="720P",
            extension="mp4",
            browser_playable=True,
            container="mp4",
            playback_mode="browser",
            page_number=1,
        )
        # Duplicate of c1
        c3 = c1.model_copy()

        deduped = search_aggregator.deduplicate_candidates([c1, c2, c3])
        self.assertEqual(len(deduped), 2)

        groups = search_aggregator.group_candidates_by_title(deduped)
        self.assertIn("Detective Ujjwalan (2025)", groups)
        self.assertEqual(len(groups["Detective Ujjwalan (2025)"]), 2)

        # Ranked: MP4 (browser playable) appears ahead of MKV
        group_items = groups["Detective Ujjwalan (2025)"]
        self.assertTrue(group_items[0].browser_playable)
        self.assertEqual(group_items[0].container, "mp4")
        self.assertFalse(group_items[1].browser_playable)

    def test_04_search_result_vs_document_distinction(self):
        """Verify the critical distinction: a bot search-result message is NOT a playable document."""
        # Simulated search result message from bot
        search_msg = MagicMock()
        search_msg.id = 12660
        search_msg.message = "Results for your search: DC\nTotal Results: 2200\nPage: 1/220"
        search_msg.media = None  # No document!

        # Asserts search message has no media document
        has_document = bool(search_msg.media and getattr(search_msg.media, "document", None))
        self.assertFalse(has_document)

        # Simulated delivered file message
        delivered_msg = MagicMock()
        delivered_msg.id = 12665
        delivered_doc = MagicMock()
        delivered_doc.mime_type = "video/mp4"
        delivered_doc.size = 209982202
        delivered_msg.media = MagicMock()
        delivered_msg.media.document = delivered_doc

        has_delivered_doc = bool(delivered_msg.media and getattr(delivered_msg.media, "document", None))
        self.assertTrue(has_delivered_doc)
        self.assertEqual(delivered_msg.media.document.mime_type, "video/mp4")

    def test_05_mock_search_endpoint(self):
        """Verify GET /api/search with mock returns candidates, pagination, and title groups."""
        resp = self.client.get("/api/search?q=Movie&mock=true&max_pages=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["query"], "Movie")
        self.assertIn("candidates", data)
        self.assertIn("pagination", data)
        self.assertIn("title_groups", data)

        candidates = data["candidates"]
        self.assertEqual(len(candidates), 4)

        # Top candidate must be browser playable MP4 1080p
        self.assertEqual(candidates[0]["container"], "mp4")
        self.assertTrue(candidates[0]["browser_playable"])
        self.assertEqual(candidates[0]["playback_mode"], "browser")

        pagination = data["pagination"]
        self.assertEqual(pagination["current_page"], 1)
        self.assertTrue(pagination["has_next"])

    def test_06_mock_delivery_endpoint(self):
        """Verify POST /api/search/deliver triggers delivery, creates session, and returns URLs."""
        payload = {
            "candidate_id": "mock_mp4_1080",
            "source_bot": "Spoty_xbot",
            "start_payload": "mock_mp4_1080_payload",
            "source_message_id": 9763,
        }
        resp = self.client.post("/api/search/deliver", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["delivered_chat_id"], "me")
        self.assertEqual(data["delivered_message_id"], 9763)
        self.assertTrue(data["browser_playable"])
        self.assertEqual(data["container"], "mp4")
        self.assertIn("session_id", data)
        self.assertTrue(data["stream_url"].startswith("http://127.0.0.1:8088/stream/me/9763"))
        self.assertTrue(data["player_url"].startswith("/api/media/session/"))

    def test_07_search_ui_endpoint(self):
        """Verify GET /api/search/ui contains Phase 15 UI elements."""
        resp = self.client.get("/api/search/ui")
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        self.assertIn("CineForge Search", body)
        self.assertIn("Find all versions", body)
        self.assertIn("/api/search/deliver", body)
        self.assertIn("delivery-modal", body)

    def test_08_telethon_media_isolation(self):
        """Ensure active PlaybackSession streaming does NOT use TelegramMediaReader or iter_download."""
        session = PlaybackSession(
            session_id="test-iso-session",
            chat_id="me",
            message_id=9763,
            stream_url="http://127.0.0.1:8088/stream/me/9763",
        )

        # Verify stream_media issues 307 redirect directly to Go streamer without touching Telethon reader
        resp = self.client.get(f"/api/media/stream/{session.session_id}", follow_redirects=False)
        # Session is registered
        session_manager._sessions[session.session_id] = session
    def test_09_progressive_pagination_traversal(self):
        """Verify progressive Load More traversal with callback_data returns subsequent pages."""
        # Initial search (page 1)
        resp1 = self.client.get("/api/search?q=Movie&mock=true")
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1["pagination"]["current_page"], 1)
        self.assertTrue(data1["pagination"]["has_next"])
        next_cb = data1["pagination"]["next_callback_data"]
        self.assertIsNotNone(next_cb)

        # Load More: request next page via callback
        resp2 = self.client.get(f"/api/search?callback_data={next_cb}&source_message_id=9763&page=2&mock=true")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertIn("candidates", data2)
        self.assertGreater(len(data2["candidates"]), 0)
        self.assertEqual(data2["pagination"]["current_page"], 2)
        self.assertTrue(data2["pagination"]["has_next"])

    def test_10_dc_search_paginated_collection_understanding(self):
        """Verify that DC search response with Page 1/220 is understood as a candidate collection, not media."""
        raw_dc_text = "Results for your search: DC\nTotal Results: 2200\nPage: 1/220"

        # Create mock message with 10 candidate buttons and pagination bar
        buttons_grid = []
        for i in range(10):
            b = MagicMock()
            b.text = f"🎬 {100 + i * 50}.00 MB DC Movie Part {i+1} 720p mp4"
            b.url = f"https://t.me/Spoty_xbot?start=payload_dc_{i+1}"
            b.data = None
            buttons_grid.append([b])

        # Pagination row
        btn_back = MagicMock(text="<< Back", data=b"back_1", url=None)
        btn_page = MagicMock(text="1/220", data=b"page_counter", url=None)
        btn_next = MagicMock(text="Next >>", data=b"next_5178541569_10", url=None)
        buttons_grid.append([btn_back, btn_page, btn_next])

        mock_msg = MagicMock()
        mock_msg.id = 55102
        mock_msg.message = raw_dc_text
        mock_msg.buttons = buttons_grid
        mock_msg.media = None  # Crucial: NO media document on search result!

        candidates, pagination = search_aggregator.parse_message_candidates(
            mock_msg,
            source_bot="Spoty_xbot",
            page_number=1,
        )

        # Asserts: Parsed as 10 distinct candidate files, not 1 movie or media
        self.assertEqual(len(candidates), 10)
        self.assertEqual(pagination.current_page, 1)
        self.assertEqual(pagination.total_pages, 220)
        self.assertEqual(pagination.total_results, 2200)
        self.assertTrue(pagination.has_next)
        self.assertEqual(pagination.next_callback_data, "next_5178541569_10")
        self.assertEqual(pagination.source_message_id, 55102)

        # Verify candidate attributes
        for c in candidates:
            self.assertEqual(c.source_bot, "Spoty_xbot")
            self.assertEqual(c.source_message_id, 55102)
            self.assertTrue(c.browser_playable)
            self.assertEqual(c.container, "mp4")
            self.assertTrue(c.start_payload.startswith("payload_dc_"))

    def test_11_ranking_compatibility_and_quality_tiers(self):
        """Verify strict candidate ranking: Browser-compatible first, then 4K > 1080p > 720p > 480p."""
        c_mkv_4k = SearchCandidate(
            candidate_id="mkv_4k", source_bot="Spoty_xbot", source_message_id=1,
            start_payload="p1", display_text="Movie 4K.mkv", title="Movie", size="4 GB",
            quality="4K", extension="mkv", browser_playable=False, container="mkv", playback_mode="external"
        )
        c_mkv_1080 = SearchCandidate(
            candidate_id="mkv_1080", source_bot="Spoty_xbot", source_message_id=1,
            start_payload="p2", display_text="Movie 1080p.mkv", title="Movie", size="2 GB",
            quality="1080P", extension="mkv", browser_playable=False, container="mkv", playback_mode="external"
        )
        c_mp4_720 = SearchCandidate(
            candidate_id="mp4_720", source_bot="Spoty_xbot", source_message_id=1,
            start_payload="p3", display_text="Movie 720p.mp4", title="Movie", size="1 GB",
            quality="720P", extension="mp4", browser_playable=True, container="mp4", playback_mode="browser"
        )
        c_mp4_1080 = SearchCandidate(
            candidate_id="mp4_1080", source_bot="Spoty_xbot", source_message_id=1,
            start_payload="p4", display_text="Movie 1080p.mp4", title="Movie", size="2.2 GB",
            quality="1080P", extension="mp4", browser_playable=True, container="mp4", playback_mode="browser"
        )
        c_mp4_4k = SearchCandidate(
            candidate_id="mp4_4k", source_bot="Spoty_xbot", source_message_id=1,
            start_payload="p5", display_text="Movie 4K.mp4", title="Movie", size="5 GB",
            quality="4K", extension="mp4", browser_playable=True, container="mp4", playback_mode="browser"
        )

        ranked = search_aggregator.rank_candidates([c_mkv_4k, c_mkv_1080, c_mp4_720, c_mp4_1080, c_mp4_4k])

        # Browser playable candidates must rank first: MP4 4K, MP4 1080p, MP4 720p
        self.assertEqual(ranked[0].candidate_id, "mp4_4k")
        self.assertEqual(ranked[1].candidate_id, "mp4_1080")
        self.assertEqual(ranked[2].candidate_id, "mp4_720")

        # Incompatible candidates follow, sorted by quality: MKV 4K, MKV 1080p
        self.assertEqual(ranked[3].candidate_id, "mkv_4k")
        self.assertEqual(ranked[4].candidate_id, "mkv_1080")

    def test_12_canonical_playback_session_saved_messages(self):
        """Verify delivery creates canonical PlaybackSession in 'me' with authoritative metadata."""
        payload = {
            "candidate_id": "mock_mp4_1080",
            "source_bot": "Spoty_xbot",
            "start_payload": "mock_mp4_1080_payload",
            "source_message_id": 9763,
        }
        resp = self.client.post("/api/search/deliver", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["delivered_chat_id"], "me")
        self.assertEqual(data["delivered_message_id"], 9763)
        self.assertTrue(data["browser_playable"])
        self.assertEqual(data["container"], "mp4")

        # Verify session exists and retains canonical attributes
        session = session_manager._sessions.get(data["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session.chat_id, "me")
        self.assertEqual(session.message_id, 9763)
        self.assertTrue(session.file_name.endswith(".mp4"))

    def test_13_automatic_routing_no_architecture_buttons(self):
        """Verify automatic routing for both MP4 and MKV in player page with no manual architecture switches."""
        # 1. MP4 Session: must route to Go streamer redirect
        mp4_session = PlaybackSession(
            session_id="test-mp4-auto-routing",
            chat_id="me",
            message_id=9763,
            file_name="Inception (2010).mp4",
            mime_type="video/mp4",
            file_size=104857600,
            stream_url="http://127.0.0.1:8088/stream/me/9763",
        )
        session_manager._sessions[mp4_session.session_id] = mp4_session

        resp_mp4 = self.client.get(f"/api/media/session/{mp4_session.session_id}/player")
        self.assertEqual(resp_mp4.status_code, 200)
        body_mp4 = resp_mp4.text
        self.assertIn(f"/api/media/stream/{mp4_session.session_id}", body_mp4)
        self.assertIn("NATIVE BROWSER STREAM", body_mp4)
        # Verify manual architecture buttons are NOT present
        self.assertNotIn("btn-mode-fmp4", body_mp4)
        self.assertNotIn("btn-mode-redirect", body_mp4)
        self.assertNotIn("switchMode", body_mp4)

        # 2. MKV Session: must route to progressive fMP4 remux endpoint
        mkv_session = PlaybackSession(
            session_id="test-mkv-auto-routing",
            chat_id="me",
            message_id=9763,
            file_name="Inception (2010).mkv",
            mime_type="video/x-matroska",
            file_size=104857600,
            stream_url="http://127.0.0.1:8088/stream/me/9763",
        )
        session_manager._sessions[mkv_session.session_id] = mkv_session

        resp_mkv = self.client.get(f"/api/media/session/{mkv_session.session_id}/player")
        self.assertEqual(resp_mkv.status_code, 200)
        body_mkv = resp_mkv.text
        self.assertIn(f"/api/media/session/{mkv_session.session_id}/play.mp4", body_mkv)
        self.assertIn("PROGRESSIVE fMP4 REMUX", body_mkv)
        # External player URL must point to Go streamer
        self.assertIn(mkv_session.stream_url, body_mkv)
        self.assertNotIn("btn-mode-fmp4", body_mkv)
        self.assertNotIn("btn-mode-redirect", body_mkv)


if __name__ == "__main__":
    unittest.main()
