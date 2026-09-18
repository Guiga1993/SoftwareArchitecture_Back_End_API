"""Tests for backend liveness and local runtime environment parsing."""

import unittest
from unittest.mock import patch

import app as api
from logging_config import parse_file_logging_enabled


class HealthRouteTests(unittest.TestCase):
    """Verify that backend health reports only HTTP process liveness."""

    def setUp(self):
        """Create a test client for the backend OpenAPI application."""
        self.client = api.app.test_client()

    def test_health_returns_liveness_and_correlation_id(self):
        """Return the stable liveness body and preserve caller correlation."""
        response = self.client.get(
            "/health",
            headers={"X-Correlation-ID": "backend-health-id"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "up", "service": "backend"})
        self.assertEqual(response.headers["X-Correlation-ID"], "backend-health-id")


class RuntimeConfigurationTests(unittest.TestCase):
    """Verify explicit backend development-server environment parsing."""

    def test_boolean_environment_accepts_documented_values(self):
        """Accept common explicit true and false spellings case-insensitively."""
        for value in ("1", "true", "YES", "On"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"BACKEND_DEBUG": value}, clear=True
            ):
                self.assertTrue(api.parse_boolean_environment("BACKEND_DEBUG"))

        for value in ("0", "false", "NO", "Off"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"BACKEND_DEBUG": value}, clear=True
            ):
                self.assertFalse(api.parse_boolean_environment("BACKEND_DEBUG"))

    def test_boolean_environment_rejects_ambiguous_values(self):
        """Reject values that cannot be interpreted safely as booleans."""
        with patch.dict("os.environ", {"BACKEND_DEBUG": "sometimes"}, clear=True):
            with self.assertRaisesRegex(ValueError, "BACKEND_DEBUG must be one of"):
                api.parse_boolean_environment("BACKEND_DEBUG")

    def test_backend_port_uses_default_and_validates_override(self):
        """Use port 5001 by default and reject invalid configured ports."""
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(api.get_backend_port(), 5001)
        with patch.dict("os.environ", {"BACKEND_PORT": "6001"}, clear=True):
            self.assertEqual(api.get_backend_port(), 6001)
        for value in ("invalid", "0", "65536"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"BACKEND_PORT": value}, clear=True
            ):
                with self.assertRaises(ValueError):
                    api.get_backend_port()

    def test_file_logging_environment_is_explicit(self):
        """Enable local file logs by default and parse explicit overrides."""
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(parse_file_logging_enabled())
        with patch.dict(
            "os.environ", {"BACKEND_FILE_LOGGING_ENABLED": "false"}, clear=True
        ):
            self.assertFalse(parse_file_logging_enabled())
        with patch.dict(
            "os.environ", {"BACKEND_FILE_LOGGING_ENABLED": "invalid"}, clear=True
        ):
            with self.assertRaisesRegex(ValueError, "must be one of"):
                parse_file_logging_enabled()


if __name__ == "__main__":
    unittest.main()