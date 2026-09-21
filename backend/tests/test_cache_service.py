import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.ai import AiQueryInterpretation
from app.models.search import SearchCandidate
from app.services.cache_service import CacheService, cache_service, normalize_search_query


class TestCacheService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_cache_status_endpoint(self):
        """Verify GET /api/cache/status returns status info."""
        response = self.client.get("/api/cache/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("cache_enabled", data)

    def test_normalize_search_query(self):
        """Verify search query normalization."""
        self.assertEqual(normalize_search_query("  Inception (2010)!  "), "inception 2010")
        self.assertEqual(normalize_search_query("Avatar: The Way of Water"), "avatar the way of water")

    async def test_unconfigured_cache_graceful_fallback(self):
        """When SUPABASE_URL is not set, cache operations must gracefully no-op."""
        with patch.object(settings, "SUPABASE_URL", None):
            self.assertFalse(cache_service.is_ready())
            res = await cache_service.get_cached_candidates("Inception")
            self.assertIsNone(res)
            # Saving should not raise
            await cache_service.save_candidates("Inception", [])
            await cache_service.save_stream_link("cand_1", "https://stream.url")

    async def test_cached_candidates_retrieval_mocked(self):
        """Verify conversion of Supabase database rows into SearchCandidate models."""
        mock_supabase_client = MagicMock()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.or_.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table

        mock_rows = [
            {
                "candidate_id": "cached_mp4_1080",
                "source_bot": "Spoty_xbot",
                "source_message_id": 9999,
                "start_payload": "payload_1",
                "callback_data": None,
                "display_text": "Interstellar (2014) 1080p Web-DL.mp4",
                "canonical_title": "Interstellar",
                "quality": "1080P",
                "size": "2.5 GB",
                "size_bytes": 2684354560,
                "language": "English",
                "container": "mp4",
                "stream_url": "https://stream.host/123",
                "watch_url": "https://stream.host/watch/123",
            }
        ]
        mock_res = MagicMock()
        mock_res.data = mock_rows
        mock_table.limit.return_value.execute.return_value = mock_res

        with patch.object(cache_service, "_get_client", return_value=mock_supabase_client):
            cands = await cache_service.get_cached_candidates("interstellar")
            self.assertIsNotNone(cands)
            self.assertEqual(len(cands), 1)
            self.assertEqual(cands[0].candidate_id, "cached_mp4_1080")
            self.assertEqual(cands[0].title, "Interstellar")
            self.assertTrue(cands[0].browser_playable)

    async def test_ai_query_cache_read_write(self):
        """Verify caching of CineAI prompt interpretations."""
        mock_supabase_client = MagicMock()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table

        mock_res = MagicMock()
        mock_res.data = [
            {
                "raw_query": "movie where cooper enters a wormhole",
                "canonical_title": "Interstellar",
                "year": "2014",
                "search_query": "Interstellar 2014",
                "confidence": 1.0,
                "explanation": "Resolved plot to Interstellar",
            }
        ]
        mock_table.limit.return_value.execute.return_value = mock_res

        with patch.object(cache_service, "_get_client", return_value=mock_supabase_client):
            interpretation = await cache_service.get_cached_ai_query("movie where cooper enters a wormhole")
            self.assertIsNotNone(interpretation)
            self.assertTrue(interpretation.is_refined)
            self.assertEqual(interpretation.canonical_title, "Interstellar")
            self.assertEqual(interpretation.search_query, "Interstellar 2014")

    def test_search_pipeline_cache_hit(self):
        """Verify GET /api/search returns is_cached=True on cache hit without calling Telegram."""
        fake_candidate = SearchCandidate(
            candidate_id="fast_hit_1080",
            source_bot="Spoty_xbot",
            source_message_id=1234,
            display_text="Interstellar (2014) 1080p.mp4",
            title="Interstellar",
            quality="1080P",
            browser_playable=True,
            container="mp4",
            playback_mode="browser",
            page_number=1,
        )

        with patch.object(cache_service, "get_cached_candidates", return_value=[fake_candidate]):
            response = self.client.get("/api/search?q=Interstellar")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["is_cached"])
            self.assertEqual(len(data["candidates"]), 1)
            self.assertEqual(data["candidates"][0]["candidate_id"], "fast_hit_1080")


if __name__ == "__main__":
    unittest.main()
