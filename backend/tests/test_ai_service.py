import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.ai import AiQueryInterpretation
from app.services.ai_service import AiService, ai_service


class TestAiService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_ai_status_endpoint(self):
        """Verify GET /api/ai/status returns status and model info."""
        response = self.client.get("/api/ai/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("model", data)
        self.assertEqual(data["model"], "gemini-3.5-flash-lite")

    async def test_fallback_when_unconfigured(self):
        """When GEMINI_API_KEY is unset, refine_movie_query returns clean fallback."""
        with patch.object(settings, "GEMINI_API_KEY", None):
            res = await ai_service.refine_movie_query("oppenhiemer")
            self.assertEqual(res.original_query, "oppenhiemer")
            self.assertFalse(res.is_refined)
            self.assertEqual(res.search_query, "oppenhiemer")

    async def test_fast_path_bypass_for_clean_queries(self):
        """Queries with explicit year e.g. 'Inception 2010' should bypass LLM call."""
        with patch.object(settings, "GEMINI_API_KEY", "dummy_key"):
            self.assertTrue(ai_service._should_bypass_ai("Inception 2010"))
            self.assertTrue(ai_service._should_bypass_ai("The Matrix 1999"))
            # Complex plot descriptions should NOT bypass
            self.assertFalse(ai_service._should_bypass_ai("that movie where cooper goes to space"))

    @patch("httpx.AsyncClient.post")
    async def test_refine_with_mocked_gemini(self, mock_post):
        """Verify parsing of Gemini JSON output for vague plot searches."""
        mock_gemini_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "is_refined": True,
                                        "canonical_title": "Interstellar",
                                        "year": "2014",
                                        "search_query": "Interstellar 2014",
                                        "confidence": 0.98,
                                        "explanation": "Resolved plot description to Interstellar (2014)",
                                        "suggested_queries": ["Interstellar 2014 IMAX"],
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_payload
        mock_post.return_value = mock_resp

        with patch.object(settings, "GEMINI_API_KEY", "dummy_key"):
            res = await ai_service.refine_movie_query("movie where cooper goes into a wormhole")
            self.assertTrue(res.is_refined)
            self.assertEqual(res.canonical_title, "Interstellar")
            self.assertEqual(res.year, "2014")
            self.assertEqual(res.search_query, "Interstellar 2014")
            self.assertEqual(res.confidence, 0.98)

    @patch("httpx.AsyncClient.post")
    def test_refine_api_endpoint(self, mock_post):
        """Verify POST /api/ai/refine endpoint."""
        mock_gemini_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "is_refined": True,
                                        "canonical_title": "The Shawshank Redemption",
                                        "year": "1994",
                                        "search_query": "The Shawshank Redemption 1994",
                                        "confidence": 0.99,
                                        "explanation": "Fixed spelling mistake",
                                        "suggested_queries": [],
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_payload
        mock_post.return_value = mock_resp

        with patch.object(settings, "GEMINI_API_KEY", "dummy_key"):
            response = self.client.post("/api/ai/refine?query=shawshank+redemtion")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["is_refined"])
            self.assertEqual(data["canonical_title"], "The Shawshank Redemption")

    @patch("httpx.AsyncClient.post")
    def test_recommend_api_endpoint(self, mock_post):
        """Verify POST /api/ai/recommend endpoint."""
        mock_gemini_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "recommendations": [
                                            {
                                                "title": "Shutter Island",
                                                "year": "2010",
                                                "reason": "Mind bending mystery",
                                                "search_query": "Shutter Island 2010",
                                            }
                                        ]
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_payload
        mock_post.return_value = mock_resp

        with patch.object(settings, "GEMINI_API_KEY", "dummy_key"):
            response = self.client.post(
                "/api/ai/recommend",
                json={"prompt": "psychological thrillers", "count": 1},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data["recommendations"]), 1)
            self.assertEqual(data["recommendations"][0]["title"], "Shutter Island")

    @patch("httpx.AsyncClient.post")
    def test_ask_companion_api_endpoint(self, mock_post):
        """Verify POST /api/ai/ask companion endpoint."""
        mock_gemini_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Christopher Nolan directed Inception, releasing it in 2010."}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_payload
        mock_post.return_value = mock_resp

        with patch.object(settings, "GEMINI_API_KEY", "dummy_key"):
            response = self.client.post(
                "/api/ai/ask",
                json={"movie_title": "Inception", "question": "Who directed this movie?"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("Christopher Nolan", data["answer"])

    def test_search_endpoint_includes_ai_interpretation(self):
        """Verify GET /api/search response contains ai_interpretation field."""
        response = self.client.get("/api/search?q=Inception&mock=true&use_ai=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ai_interpretation", data)
        self.assertEqual(data["query"], "Inception")


if __name__ == "__main__":
    unittest.main()
