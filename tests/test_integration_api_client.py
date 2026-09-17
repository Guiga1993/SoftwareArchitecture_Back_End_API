"""Unit tests for backend communication with the internal integration API."""

import os
import unittest
from unittest.mock import Mock, patch

import requests

from services.integration_api_client import (
    CORRELATION_HEADER,
    IntegrationAPIClient,
    IntegrationAPIError,
    IntegrationConfigurationError,
    IntegrationResponseError,
    IntegrationTimeoutError,
)


class IntegrationAPIClientTests(unittest.TestCase):
    """Verify internal HTTP behavior without contacting a running service."""

    def setUp(self):
        """Create deterministic explicit client settings independent of `.env`."""
        self.client = IntegrationAPIClient(
            "https://integration.test/root/",
            connect_timeout_seconds=2,
            read_timeout_seconds=7,
        )

    @staticmethod
    def response(status_code=200, payload=None, correlation_id="request-id"):
        """Build a mocked HTTP response with JSON and correlation metadata."""
        response = Mock(ok=200 <= status_code < 300, status_code=status_code)
        response.headers = {CORRELATION_HEADER: correlation_id}
        response.json.return_value = (
            {"success": True} if payload is None else payload
        )
        return response

    @patch("services.integration_api_client.requests.request")
    def test_valid_object_response_and_correlation_header(self, request):
        """Normalize endpoint paths, use timeout tuple, and return object JSON."""
        request.return_value = self.response(payload={"status": "up"})

        result = self.client.health(correlation_id="request-id")

        self.assertEqual(result, {"status": "up"})
        request.assert_called_once_with(
            "GET",
            "https://integration.test/root/health",
            json=None,
            headers={"Accept": "application/json", CORRELATION_HEADER: "request-id"},
            timeout=(2, 7),
        )

    @patch("services.integration_api_client.requests.request")
    def test_post_methods_use_only_allowed_internal_paths(self, request):
        """Call only address and shipping endpoints with JSON headers."""
        request.return_value = self.response()

        self.client.validate_address({"city": "Atlanta"}, correlation_id="request-id")
        self.client.shipping_quote({"parcels": []}, correlation_id="request-id")

        urls = [call.args[1] for call in request.call_args_list]
        self.assertEqual(
            urls,
            [
                "https://integration.test/root/validate-address",
                "https://integration.test/root/shipping-quote",
            ],
        )
        for call in request.call_args_list:
            self.assertEqual(call.kwargs["headers"]["Content-Type"], "application/json")

    @patch("services.integration_api_client.requests.request")
    def test_invalid_and_non_object_json_raise_response_error(self, request):
        """Reject malformed JSON and valid JSON values that are not objects."""
        invalid = self.response()
        invalid.json.side_effect = ValueError
        non_object = self.response(payload=[])

        for response in (invalid, non_object):
            with self.subTest(response=response):
                request.return_value = response
                with self.assertRaises(IntegrationResponseError):
                    self.client.health()

    @patch(
        "services.integration_api_client.requests.request",
        side_effect=requests.Timeout,
    )
    def test_timeout_raises_integration_timeout(self, _request):
        """Translate requests timeout without exposing provider concepts."""
        with self.assertRaises(IntegrationTimeoutError):
            self.client.health()

    @patch(
        "services.integration_api_client.requests.request",
        side_effect=requests.ConnectionError,
    )
    def test_connection_failure_raises_integration_api_error(self, _request):
        """Translate connection failure to the backend integration boundary."""
        with self.assertRaises(IntegrationAPIError):
            self.client.health()

    def test_http_status_mapping(self):
        """Translate integration configuration, timeout, and gateway statuses."""
        cases = (
            (503, IntegrationConfigurationError),
            (504, IntegrationTimeoutError),
            (502, IntegrationAPIError),
            (500, IntegrationAPIError),
        )
        for status, expected_error in cases:
            with self.subTest(status=status), patch(
                "services.integration_api_client.requests.request",
                return_value=self.response(status_code=status),
            ):
                with self.assertRaises(expected_error):
                    self.client.health()

    @patch("services.integration_api_client.uuid.uuid4")
    @patch("services.integration_api_client.requests.request")
    def test_generates_correlation_id_when_missing(self, request, uuid4):
        """Generate one backend identifier when the caller supplies none."""
        uuid4.return_value = "generated-id"
        request.return_value = self.response(correlation_id="generated-id")

        self.client.health()

        self.assertEqual(
            request.call_args.kwargs["headers"][CORRELATION_HEADER],
            "generated-id",
        )

    def test_configuration_requires_absolute_base_url(self):
        """Reject missing, relative, and unsupported integration locations."""
        for base_url in ("", "localhost:8001", "ftp://integration.test"):
            with self.subTest(base_url=base_url), self.assertRaises(
                IntegrationConfigurationError
            ):
                IntegrationAPIClient(base_url)

    @patch("services.integration_api_client.load_dotenv")
    def test_environment_configuration_and_invalid_timeouts(self, _load_dotenv):
        """Load only the configured service URL and positive timeout values."""
        environment = {
            "SHIPPO_INTEGRATION_BASE_URL": "https://integration.test",
            "SHIPPO_INTEGRATION_CONNECT_TIMEOUT_SECONDS": "1.5",
            "SHIPPO_INTEGRATION_READ_TIMEOUT_SECONDS": "8",
        }
        with patch.dict(os.environ, environment, clear=True):
            client = IntegrationAPIClient()
        self.assertEqual(client.base_url, "https://integration.test")
        self.assertEqual(client.timeout, (1.5, 8.0))

        with patch.dict(
            os.environ,
            {
                "SHIPPO_INTEGRATION_BASE_URL": "https://integration.test",
                "SHIPPO_INTEGRATION_READ_TIMEOUT_SECONDS": "0",
            },
            clear=True,
        ):
            with self.assertRaises(IntegrationConfigurationError):
                IntegrationAPIClient()


if __name__ == "__main__":
    unittest.main()