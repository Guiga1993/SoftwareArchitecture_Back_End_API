"""Adapt backend address requests to the internal integration HTTP service.

This application service knows the internal `/validate-address` JSON contract
and the frontend response shape. It contains no provider authentication,
provider endpoint, provider payload, retry, or raw provider parsing logic.
"""

from typing import Any

from services.integration_api_client import (
    IntegrationAPIClient,
    IntegrationResponseError,
)


def validate_address(
    customer_name: str,
    street1: str,
    city: str,
    state: str,
    zip_code: str,
    country: str = "US",
    *,
    correlation_id: str | None = None,
    client: IntegrationAPIClient | None = None,
) -> dict[str, Any]:
    """Validate one address and preserve the backend's frontend-facing result.

    Args:
        customer_name: Person or company associated with the destination.
        street1: Primary street address line.
        city: Destination city.
        state: Two-letter US state code.
        zip_code: ZIP or ZIP+4 postal code.
        country: Country code retained for the internal HTTP contract.
        correlation_id: Optional backend request identifier forwarded downstream.
        client: Optional integration client used by unit tests.

    Returns:
        The established backend response with success, validity, normalized ZIP,
        residential status, and integration messages.

    Raises:
        IntegrationResponseError: The integration HTTP response is incomplete
            or contains an unexpected technical business error.
    """
    integration_client = client or IntegrationAPIClient()
    response = integration_client.validate_address(
        {
            "customer_name": customer_name,
            "street1": street1,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
        },
        correlation_id=correlation_id,
    )

    required_fields = {
        "success",
        "valid",
        "normalized_zip",
        "is_residential",
        "messages",
    }
    if not required_fields <= response.keys() or not isinstance(
        response.get("messages"), list
    ):
        raise IntegrationResponseError(
            "Integration API returned an invalid address result."
        )

    error_code = response.get("error_code")
    if error_code not in (None, "INVALID_ADDRESS"):
        raise IntegrationResponseError(
            "Integration API returned an unexpected address error result."
        )

    # Invalidity is a completed business outcome in the backend contract.
    return {
        "success": True,
        "valid": bool(response["valid"]),
        "normalized_zip": response["normalized_zip"],
        "is_residential": response["is_residential"],
        "messages": response["messages"],
    }