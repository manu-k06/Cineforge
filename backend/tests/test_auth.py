import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.auth import auth_service


class TestAuthEndpointsAndService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_auth_status_endpoint(self):
        """Verify GET /api/auth/status returns status."""
        response = self.client.get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("configured", data)

    def test_auth_me_unauthorized_when_missing_token(self):
        """GET /api/auth/me should return 401 when no token is supplied."""
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("credentials were not provided", response.json().get("detail", ""))

    def test_auth_me_unauthorized_when_invalid_token(self):
        """GET /api/auth/me should return 401 when token verification fails."""
        with patch.object(auth_service, "verify_token", return_value=None):
            response = self.client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer invalid_token_123"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid or expired authentication token", response.json().get("detail", ""))

    def test_auth_me_success_with_valid_token(self):
        """GET /api/auth/me should return user profile with valid Bearer token."""
        mock_user = {
            "id": "user-uuid-12345",
            "email": "cinephile@example.com",
            "user_metadata": {"full_name": "Test Cinephile"},
            "app_metadata": {"provider": "email"},
        }
        with patch.object(auth_service, "verify_token", return_value=mock_user):
            response = self.client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer valid_token_123"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "authenticated")
            self.assertEqual(data.get("user", {}).get("email"), "cinephile@example.com")
            self.assertEqual(data.get("user", {}).get("user_metadata", {}).get("full_name"), "Test Cinephile")

    def test_auth_service_verify_token_with_mocked_supabase(self):
        """Verify auth_service parses Supabase GoTrue user response correctly."""
        mock_user_obj = MagicMock()
        mock_user_obj.id = "supa-id-789"
        mock_user_obj.email = "streamer@cineforge.app"
        mock_user_obj.user_metadata = {"full_name": "Streamer Pro"}
        mock_user_obj.app_metadata = {}

        mock_user_response = MagicMock()
        mock_user_response.user = mock_user_obj

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_user_response

        with patch.object(auth_service, "_get_client", return_value=mock_client):
            result = auth_service.verify_token("test-valid-jwt")
            self.assertIsNotNone(result)
            self.assertEqual(result["id"], "supa-id-789")
            self.assertEqual(result["email"], "streamer@cineforge.app")
            self.assertEqual(result["user_metadata"]["full_name"], "Streamer Pro")
