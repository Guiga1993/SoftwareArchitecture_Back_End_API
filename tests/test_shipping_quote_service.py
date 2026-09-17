"""Unit tests for backend shipping adaptation to the integration API."""

import unittest
from unittest.mock import Mock

from services.integration_api_client import IntegrationResponseError
from services.shipping_quote_service import calculate_shipping_quote


class ShippingQuoteServiceTests(unittest.TestCase):
    """Verify freight policy, parcel expansion, and frontend result adaptation."""

    def quote(self, client, **overrides):
        """Call the service with reusable trusted generator and destination data."""
        values = {
            "origin_name": "Origin Company",
            "origin_street": "123 Origin Street",
            "origin_city": "Torrance",
            "origin_state": "ca",
            "origin_zip": "90504",
            "customer_name": "John Doe",
            "destination_street": "1 CNN Center",
            "destination_city": "Atlanta",
            "destination_state": "ga",
            "destination_zip": "30303",
            "generator_quantity": 2,
            "weight_lb": 12,
            "length_in": 24,
            "width_in": 16,
            "height_in": 12,
            "correlation_id": "request-id",
            "client": client,
        }
        values.update(overrides)
        return calculate_shipping_quote(**values)

    def test_builds_parcels_and_adapts_successful_quote(self):
        """Send trusted measurements and preserve the frontend success contract."""
        client = Mock()
        client.shipping_quote.return_value = {
            "success": True,
            "carrier": "USPS",
            "service": "Priority",
            "amount": "72.10",
            "currency": "USD",
            "estimated_days": 3,
        }

        result = self.quote(client)

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Shipping rates available.",
                "carrier": "USPS",
                "service": "Priority",
                "amount": "72.10",
                "currency": "USD",
                "estimated_days": 3,
            },
        )
        client.shipping_quote.assert_called_once_with(
            {
                "address_from": {
                    "name": "Origin Company",
                    "street1": "123 Origin Street",
                    "city": "Torrance",
                    "state": "CA",
                    "zip": "90504",
                    "country": "US",
                },
                "address_to": {
                    "name": "John Doe",
                    "street1": "1 CNN Center",
                    "city": "Atlanta",
                    "state": "GA",
                    "zip": "30303",
                    "country": "US",
                },
                "parcels": [
                    {
                        "length": "24",
                        "width": "16",
                        "height": "12",
                        "distance_unit": "in",
                        "weight": "12",
                        "mass_unit": "lb",
                    },
                    {
                        "length": "24",
                        "width": "16",
                        "height": "12",
                        "distance_unit": "in",
                        "weight": "12",
                        "mass_unit": "lb",
                    },
                ],
            },
            correlation_id="request-id",
        )

    def test_adapts_no_rates_and_normalized_messages(self):
        """Preserve the backend no-rate wording and normalized message objects."""
        client = Mock()
        client.shipping_quote.return_value = {
            "success": False,
            "error_code": "NO_RATES",
            "message": "No shipping rates available.",
            "shippo_messages": [
                {"source": "UPS", "message": "Parcel is too large."}
            ],
        }

        result = self.quote(client, generator_quantity=1)

        self.assertEqual(
            result,
            {
                "success": False,
                "error_code": "NO_RATES",
                "message": "No shipping rate was available for the supplied shipment.",
                "shippo_messages": [
                    {"source": "UPS", "message": "Parcel is too large."}
                ],
            },
        )

    def test_rejects_oversized_parcel_without_integration_call(self):
        """Keep the backend-owned freight eligibility rule before HTTP integration."""
        client = Mock()

        result = self.quote(
            client,
            generator_quantity=1,
            length_in=48,
            width_in=40,
            height_in=60,
        )

        self.assertEqual(
            result,
            {
                "success": False,
                "message": (
                    "This generator exceeds the standard parcel size limit "
                    "and requires a freight quote."
                ),
                "shippo_messages": [],
            },
        )
        client.shipping_quote.assert_not_called()

    def test_rejects_malformed_integration_responses(self):
        """Reject incomplete success, unexpected error, and malformed messages."""
        responses = (
            {"success": True, "carrier": "UPS"},
            {"success": False, "error_code": "SHIPPO_FAILURE"},
            {
                "success": False,
                "error_code": "NO_RATES",
                "shippo_messages": ["raw string"],
            },
        )
        for response in responses:
            with self.subTest(response=response):
                client = Mock()
                client.shipping_quote.return_value = response
                with self.assertRaises(IntegrationResponseError):
                    self.quote(client)


if __name__ == "__main__":
    unittest.main()
