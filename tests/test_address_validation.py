"""Endpoint tests for POST /validate-address using a mocked application service."""

import unittest
from unittest.mock import patch

import app as api
from services.integration_api_client import (
    IntegrationAPIError,
    IntegrationConfigurationError,
    IntegrationResponseError,
    IntegrationTimeoutError,
)


class AddressValidationEndpointTests(unittest.TestCase):
    """Verify request binding, orchestration, and technical error mapping."""

    def setUp(self):
        """Create a Flask client and one complete US address request."""
        self.client = api.app.test_client()
        self.payload = {
            "customer_name": "John Doe",
            "street1": "123 Main Street",
            "city": "Atlanta",
            "state": "GA",
            "zip_code": "30301",
        }

    @patch("app.validate_address")
    def test_valid_address(self, validate_address):
        """Return a normalized valid-address response and call the service once."""
        validate_address.return_value = {
            "success": True,
            "valid": True,
            "normalized_zip": "30301-1234",
            "is_residential": True,
            "messages": [],
        }

        response = self.client.post(
            "/validate-address",
            json=self.payload,
            headers={"X-Correlation-ID": "address-request-id"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), validate_address.return_value)
        self.assertEqual(
            response.headers["X-Correlation-ID"], "address-request-id"
        )
        validate_address.assert_called_once_with(
            customer_name="John Doe",
            street1="123 Main Street",
            city="Atlanta",
            state="GA",
            zip_code="30301",
            correlation_id="address-request-id",
        )

    @patch("app.validate_address")
    def test_invalid_address_is_a_successful_business_response(self, validate_address):
        """Return HTTP 200 with valid=false when Shippo processes the address."""
        validate_address.return_value = {
            "success": True,
            "valid": False,
            "normalized_zip": None,
            "is_residential": None,
            "messages": [{"text": "Street could not be validated."}],
        }

        response = self.client.post("/validate-address", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), validate_address.return_value)

    @patch(
        "app.validate_address",
        side_effect=IntegrationTimeoutError("raw timeout detail"),
    )
    def test_timeout_returns_504(self, _validate_address):
        """Map Shippo timeout failures to a safe ErrorSchema response."""
        response = self.client.post("/validate-address", json=self.payload)

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.get_json(), {"message": "Address validation timed out."})
        self.assertNotIn("raw timeout detail", response.get_data(as_text=True))

    def test_provider_failures_return_502(self):
        """Map Shippo HTTP and malformed-response failures to HTTP 502."""
        for error in (
            IntegrationAPIError("raw provider detail"),
            IntegrationResponseError("raw response detail"),
        ):
            with self.subTest(error=type(error).__name__), patch(
                "app.validate_address", side_effect=error
            ):
                response = self.client.post("/validate-address", json=self.payload)

                self.assertEqual(response.status_code, 502)
                self.assertEqual(
                    response.get_json(),
                    {"message": "Unable to validate address with Shippo."},
                )
                self.assertNotIn("raw", response.get_data(as_text=True))

    @patch(
        "app.validate_address",
        side_effect=IntegrationConfigurationError("raw configuration detail"),
    )
    def test_configuration_failure_returns_503(self, _validate_address):
        """Map missing Shippo credentials to service unavailable."""
        response = self.client.post("/validate-address", json=self.payload)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {"message": "Address validation is not configured."},
        )
        self.assertNotIn("raw configuration detail", response.get_data(as_text=True))

    @patch("app.validate_address", side_effect=RuntimeError("raw secret detail"))
    def test_unexpected_failure_returns_500(self, _validate_address):
        """Map unexpected defects to HTTP 500 without exposing exception text."""
        with patch("app.logger") as logger:
            response = self.client.post("/validate-address", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"message": "Unable to validate address."})
        self.assertNotIn("raw secret detail", response.get_data(as_text=True))
        logger.exception.assert_called_once_with("Unexpected address validation failure")

    @patch("app.validate_address")
    def test_malformed_body_uses_framework_422(self, validate_address):
        """Leave malformed request handling to flask-openapi3 validation."""
        malformed = {**self.payload}
        malformed.pop("street1")

        response = self.client.post("/validate-address", json=malformed)

        self.assertEqual(response.status_code, 422)
        validate_address.assert_not_called()

    def test_route_and_openapi_tag_are_registered(self):
        """Expose POST /validate-address under the Address Validation tag."""
        route = next(
            rule for rule in api.app.url_map.iter_rules()
            if rule.rule == "/validate-address"
        )
        operation = api.app.api_doc["paths"]["/validate-address"]["post"]

        self.assertIn("POST", route.methods)
        self.assertEqual(operation["tags"], ["Address Validation"])
        self.assertTrue(
            {"200", "500", "502", "503", "504"}
            <= set(operation["responses"])
        )


if __name__ == "__main__":
    unittest.main()