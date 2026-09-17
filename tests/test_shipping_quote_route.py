"""Route-level tests for POST /shipping-quote with mocked dependencies."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app as api
from services.integration_api_client import (
    IntegrationAPIError,
    IntegrationConfigurationError,
    IntegrationResponseError,
    IntegrationTimeoutError,
)


class ShippingQuoteRouteTests(unittest.TestCase):
    """Verify route orchestration, status mapping, and session lifecycle."""

    def setUp(self):
        """Create a Flask client, valid request, and mocked generator session."""
        self.client = api.app.test_client()
        self.payload = {
            "origin_name": "Sender Company",
            "customer_name": "Customer Company",
            "origin_street": "1 Main Street",
            "origin_city": "Torrance",
            "origin_state": "CA",
            "origin_zip": "90501",
            "destination_street": "2 Oak Street",
            "destination_city": "Atlanta",
            "destination_state": "GA",
            "destination_zip": "30301",
            "generator_id": 1,
            "generator_quantity": 2,
        }
        self.generator = SimpleNamespace(
            weight_lb=12,
            length_in=24,
            width_in=16,
            height_in=12,
        )
        self.session = Mock()
        self.session.query.return_value.filter.return_value.first.return_value = (
            self.generator
        )
        self.session_patcher = patch("app.Session", return_value=self.session)
        self.session_patcher.start()

    def tearDown(self):
        """Restore the session factory after each route test."""
        self.session_patcher.stop()

    @patch("app.calculate_shipping_quote")
    def test_successful_quote_returns_200(self, calculate_shipping_quote):
        """Return a successful rate and forward generator measurements."""
        calculate_shipping_quote.return_value = {
            "success": True,
            "message": "Shipping rates available.",
            "carrier": "USPS",
            "service": "Priority",
            "amount": "12.00",
            "currency": "USD",
            "estimated_days": 3,
        }

        response = self.client.post(
            "/shipping-quote",
            json=self.payload,
            headers={"X-Correlation-ID": "quote-request-id"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), calculate_shipping_quote.return_value)
        self.assertEqual(response.headers["X-Correlation-ID"], "quote-request-id")
        calculate_shipping_quote.assert_called_once_with(
            origin_name="Sender Company",
            origin_street="1 Main Street",
            origin_city="Torrance",
            origin_state="CA",
            origin_zip="90501",
            customer_name="Customer Company",
            destination_street="2 Oak Street",
            destination_city="Atlanta",
            destination_state="GA",
            destination_zip="30301",
            generator_quantity=2,
            weight_lb=12,
            length_in=24,
            width_in=16,
            height_in=12,
            correlation_id="quote-request-id",
        )
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote")
    def test_no_rates_business_result_returns_200(self, calculate_shipping_quote):
        """Preserve a completed no-rates result as HTTP 200."""
        calculate_shipping_quote.return_value = {
            "success": False,
            "error_code": "NO_RATES",
            "message": "No shipping rate was available for the supplied shipment.",
            "shippo_messages": [
                {"source": "Shippo", "message": "Unavailable"}
            ],
        }

        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), calculate_shipping_quote.return_value)
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote")
    def test_missing_generator_returns_404(self, calculate_shipping_quote):
        """Return not found without invoking Shippo when the generator is absent."""
        self.session.query.return_value.filter.return_value.first.return_value = None

        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"message": "Hydrogen generator not found."})
        calculate_shipping_quote.assert_not_called()
        self.session.close.assert_called_once()

    @patch(
        "app.calculate_shipping_quote",
        side_effect=IntegrationConfigurationError("raw"),
    )
    def test_configuration_failure_returns_503(self, _calculate_shipping_quote):
        """Map unavailable shipping configuration to HTTP 503."""
        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {"message": "Shipping service configuration is unavailable."},
        )
        self.assertNotIn("raw", response.get_data(as_text=True))
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote", side_effect=IntegrationTimeoutError("raw"))
    def test_timeout_returns_504(self, _calculate_shipping_quote):
        """Map provider timeout to HTTP 504 without exposing exception text."""
        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 504)
        self.assertEqual(
            response.get_json(),
            {"message": "The shipping provider did not respond in time."},
        )
        self.assertNotIn("raw", response.get_data(as_text=True))
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote", side_effect=IntegrationAPIError("raw"))
    def test_api_failure_returns_502(self, _calculate_shipping_quote):
        """Map provider communication failure to HTTP 502."""
        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {"message": "Unable to communicate with the shipping provider."},
        )
        self.assertNotIn("raw", response.get_data(as_text=True))
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote", side_effect=IntegrationResponseError("raw"))
    def test_response_failure_returns_502(self, _calculate_shipping_quote):
        """Map malformed provider responses to a distinct safe HTTP 502 body."""
        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {"message": "The shipping provider returned an invalid response."},
        )
        self.assertNotIn("raw", response.get_data(as_text=True))
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote", side_effect=RuntimeError("raw secret detail"))
    def test_unexpected_failure_returns_500(self, _calculate_shipping_quote):
        """Map unexpected defects to HTTP 500 and retain traceback logging."""
        with patch("app.logger") as logger:
            response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"message": "Unexpected server error."})
        self.assertNotIn("raw secret detail", response.get_data(as_text=True))
        logger.exception.assert_called_once_with("Unexpected shipping quote failure")
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote")
    def test_malformed_request_uses_framework_422(self, calculate_shipping_quote):
        """Leave malformed body handling to flask-openapi3 validation."""
        malformed = {**self.payload}
        malformed.pop("generator_id")

        response = self.client.post("/shipping-quote", json=malformed)

        self.assertEqual(response.status_code, 422)
        calculate_shipping_quote.assert_not_called()
        self.assertFalse(self.session.close.called)

    @patch("app.calculate_shipping_quote")
    def test_invalid_shipping_addresses_use_framework_422(
        self, calculate_shipping_quote
    ):
        """Reject missing, blank, invalid-state, and invalid-ZIP address data."""
        cases = (
            {key: value for key, value in self.payload.items() if key != "origin_street"},
            {**self.payload, "origin_name": "   "},
            {**self.payload, "origin_state": "C"},
            {**self.payload, "destination_state": "Georgia"},
            {**self.payload, "origin_zip": "9050"},
            {**self.payload, "destination_zip": "30301-12"},
        )
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/shipping-quote", json=payload)
                self.assertEqual(response.status_code, 422)

        calculate_shipping_quote.assert_not_called()

    @patch("app.calculate_shipping_quote")
    def test_database_failure_returns_500_and_closes_session(
        self, calculate_shipping_quote
    ):
        """Treat database defects as internal errors rather than provider failures."""
        self.session.query.side_effect = RuntimeError("raw database detail")

        response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"message": "Unexpected server error."})
        self.assertNotIn("raw database detail", response.get_data(as_text=True))
        calculate_shipping_quote.assert_not_called()
        self.session.close.assert_called_once()

    @patch("app.calculate_shipping_quote")
    def test_session_construction_failure_returns_500(
        self, calculate_shipping_quote
    ):
        """Return ErrorSchema JSON even when session construction itself fails."""
        with patch("app.Session", side_effect=RuntimeError("raw database detail")):
            response = self.client.post("/shipping-quote", json=self.payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"message": "Unexpected server error."})
        self.assertNotIn("raw database detail", response.get_data(as_text=True))
        calculate_shipping_quote.assert_not_called()

    def test_openapi_documents_all_shipping_outcomes(self):
        """Expose all explicit route outcomes while leaving 422 framework-managed."""
        operation = api.app.api_doc["paths"]["/shipping-quote"]["post"]

        self.assertTrue(
            {"200", "404", "500", "502", "503", "504"}
            <= set(operation["responses"])
        )


if __name__ == "__main__":
    unittest.main()