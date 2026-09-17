"""Unit tests for backend address adaptation to the integration API."""

import unittest
from unittest.mock import Mock

from services.address_validation_service import validate_address
from services.integration_api_client import IntegrationResponseError


class AddressValidationServiceTests(unittest.TestCase):
    """Verify the internal HTTP contract and stable frontend result shape."""

    def test_forwards_request_and_adapts_valid_address(self):
        """Forward exact integration JSON and preserve normalized backend fields."""
        client = Mock()
        client.validate_address.return_value = {
            "success": True,
            "valid": True,
            "normalized_zip": "90501-1234",
            "is_residential": False,
            "messages": [{"text": "Address matched."}],
        }

        result = validate_address(
            "Honda",
            "1919 Torrance Blvd",
            "Torrance",
            "CA",
            "90501",
            correlation_id="request-id",
            client=client,
        )

        self.assertEqual(
            result,
            {
                "success": True,
                "valid": True,
                "normalized_zip": "90501-1234",
                "is_residential": False,
                "messages": [{"text": "Address matched."}],
            },
        )
        client.validate_address.assert_called_once_with(
            {
                "customer_name": "Honda",
                "street1": "1919 Torrance Blvd",
                "city": "Torrance",
                "state": "CA",
                "zip_code": "90501",
                "country": "US",
            },
            correlation_id="request-id",
        )

    def test_invalid_address_remains_successful_business_result(self):
        """Normalize INVALID_ADDRESS to the backend's existing HTTP-200 contract."""
        client = Mock()
        client.validate_address.return_value = {
            "success": False,
            "valid": False,
            "normalized_zip": None,
            "is_residential": None,
            "messages": [{"text": "Invalid"}],
            "error_code": "INVALID_ADDRESS",
            "message": "Address is invalid.",
        }

        result = validate_address(
            "Honda", "Street", "City", "CA", "90501", client=client
        )

        self.assertEqual(result["success"], True)
        self.assertEqual(result["valid"], False)
        self.assertEqual(result["messages"], [{"text": "Invalid"}])
        self.assertNotIn("error_code", result)

    def test_rejects_malformed_or_unexpected_integration_results(self):
        """Raise IntegrationResponseError for incomplete or technical responses."""
        responses = (
            {"success": True},
            {
                "success": False,
                "valid": False,
                "normalized_zip": None,
                "is_residential": None,
                "messages": [],
                "error_code": "SHIPPO_FAILURE",
            },
        )
        for response in responses:
            with self.subTest(response=response):
                client = Mock()
                client.validate_address.return_value = response
                with self.assertRaises(IntegrationResponseError):
                    validate_address(
                        "Honda", "Street", "City", "CA", "90501", client=client
                    )


if __name__ == "__main__":
    unittest.main()
