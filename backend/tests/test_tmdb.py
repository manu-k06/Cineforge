import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.metadata import MovieMetadata, TrendingMoviesResponse
from app.services.tmdb import sanitize_movie_query, tmdb_service


class TestTmdbMetadataService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        tmdb_service._cache.clear()
        tmdb_service._trending_cache.clear()

    def test_sanitize_movie_query(self):
        """Verify messy torrent/release filenames are cleanly sanitized."""
        title, year = sanitize_movie_query("Inception.2010.1080p.BluRay.x264")
        self.assertEqual(title, "Inception")
        self.assertEqual(year, 2010)

        title, year = sanitize_movie_query("Avatar: The Way of Water (2022) [4K UHD]")
        self.assertEqual(title, "Avatar: The Way of Water")
        self.assertEqual(year, 2022)

        title, year = sanitize_movie_query("Interstellar")
        self.assertEqual(title, "Interstellar")
        self.assertIsNone(year)

    def test_metadata_status_endpoint(self):
        """GET /api/metadata/status returns current configuration status."""
        response = self.client.get("/api/metadata/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("configured", data)

    async def test_unconfigured_fallback(self):
        """When TMDB_API_KEY is not set, service gracefully returns fallback metadata."""
        with patch.object(settings, "TMDB_API_KEY", None):
            self.assertFalse(tmdb_service.is_configured())
            meta = await tmdb_service.search_and_get_metadata("The Dark Knight 2008")
            self.assertIsInstance(meta, MovieMetadata)
            self.assertEqual(meta.title, "The Dark Knight")
            self.assertEqual(meta.year, "2008")
            self.assertEqual(meta.source, "fallback")

    async def test_search_and_get_metadata_mocked_success(self):
        """Verify successful TMDb search, details, credits, and video parsing."""
        search_payload = {
            "results": [
                {
                    "id": 27205,
                    "title": "Inception",
                    "original_title": "Inception",
                    "overview": "Cobb steals information from targets by entering their dreams.",
                    "release_date": "2010-07-15",
                    "vote_average": 8.36,
                    "vote_count": 34000,
                    "poster_path": "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
                    "backdrop_path": "/s3TBrRGB1iav7gFOCNx3H31MoES.jpg",
                }
            ]
        }

        details_payload = {
            "id": 27205,
            "title": "Inception",
            "original_title": "Inception",
            "overview": "Cobb steals information from targets by entering their dreams.",
            "release_date": "2010-07-15",
            "vote_average": 8.36,
            "vote_count": 34000,
            "runtime": 148,
            "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}],
            "poster_path": "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
            "backdrop_path": "/s3TBrRGB1iav7gFOCNx3H31MoES.jpg",
            "credits": {
                "cast": [
                    {
                        "name": "Leonardo DiCaprio",
                        "character": "Dom Cobb",
                        "profile_path": "/wo2Syst399nUuqSTqNF8QIvTGwE.jpg",
                    },
                    {
                        "name": "Joseph Gordon-Levitt",
                        "character": "Arthur",
                        "profile_path": "/dhv9fGgP1dFf9G.jpg",
                    },
                ],
                "crew": [
                    {"name": "Christopher Nolan", "job": "Director"},
                    {"name": "Hans Zimmer", "job": "Original Music Composer"},
                ],
            },
            "videos": {
                "results": [
                    {"key": "YoHD9XEInc0", "site": "YouTube", "type": "Trailer"}
                ]
            },
        }

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = search_payload

        mock_details_resp = MagicMock()
        mock_details_resp.status_code = 200
        mock_details_resp.json.return_value = details_payload

        with patch.object(settings, "TMDB_API_KEY", "test_mock_tmdb_key"):
            with patch("httpx.AsyncClient.get", side_effect=[mock_search_resp, mock_details_resp]):
                meta = await tmdb_service.search_and_get_metadata("Inception", 2010)

                self.assertEqual(meta.tmdb_id, 27205)
                self.assertEqual(meta.title, "Inception")
                self.assertEqual(meta.year, "2010")
                self.assertEqual(meta.rating, 8.4)
                self.assertEqual(meta.runtime, 148)
                self.assertIn("Action", meta.genres)
                self.assertIn("https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg", meta.poster_url)
                self.assertIn("https://image.tmdb.org/t/p/w1280/s3TBrRGB1iav7gFOCNx3H31MoES.jpg", meta.backdrop_url)
                self.assertEqual(meta.trailer_key, "YoHD9XEInc0")
                self.assertEqual(meta.directors, ["Christopher Nolan"])
                self.assertEqual(len(meta.cast), 2)
                self.assertEqual(meta.cast[0].name, "Leonardo DiCaprio")
                self.assertEqual(meta.cast[0].character, "Dom Cobb")

    def test_api_metadata_movie_endpoint(self):
        """GET /api/metadata/movie endpoint returns MovieMetadata model."""
        response = self.client.get("/api/metadata/movie?title=Inception&year=2010")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("title"), "Inception")

    def test_api_metadata_trending_endpoint(self):
        """GET /api/metadata/trending endpoint returns TrendingMoviesResponse model."""
        response = self.client.get("/api/metadata/trending?time_window=week&page=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    async def test_search_movie_suggestions_mocked(self):
        """Verify search_movie_suggestions parses TMDb search results into clean suggestions."""
        mock_payload = {
            "results": [
                {
                    "id": 157336,
                    "title": "Interstellar",
                    "release_date": "2014-11-05",
                    "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
                    "vote_average": 8.4,
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch.object(settings, "TMDB_API_KEY", "test_mock_tmdb_key"):
            with patch("httpx.AsyncClient.get", return_value=mock_resp):
                suggestions = await tmdb_service.search_movie_suggestions("interstelar", limit=3)
                self.assertEqual(len(suggestions), 1)
                self.assertEqual(suggestions[0]["title"], "Interstellar")
                self.assertEqual(suggestions[0]["year"], "2014")
                self.assertIn("/w185/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", suggestions[0]["poster_url"])

    def test_api_search_suggestions_endpoint(self):
        """GET /api/search/suggestions returns 200 with suggestions list."""
        response = self.client.get("/api/search/suggestions?q=Inception")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggestions", data)
        self.assertIsInstance(data["suggestions"], list)
