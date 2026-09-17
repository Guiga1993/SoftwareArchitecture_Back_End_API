"""Apply backend freight policy and adapt integration API shipping results.

The backend owns caller-address adaptation, generator quantity, trusted database
measurements, and freight eligibility. The integration API owns provider
payloads, retries, rate selection, and provider response interpretation.
"""

from typing import Any

from services.integration_api_client import (
    IntegrationAPIClient,
    IntegrationResponseError,
)


# Backend-owned freight eligibility rule for standard US parcel processing.
MAX_PARCEL_LENGTH_PLUS_GIRTH_IN = 165


def _calculate_length_plus_girth(
    length_in: float,
    width_in: float,
    height_in: float,
) -> float:
    """Return longest side plus twice the sum of the other packaged sides."""
    longest_side, side_a, side_b = sorted(
        (length_in, width_in, height_in),
        reverse=True,
    )
    return longest_side + 2 * (side_a + side_b)


def _build_parcels(
    generator_quantity: int,
    weight_lb: float,
    length_in: float,
    width_in: float,
    height_in: float,
) -> list[dict[str, str]]:
    """Expand trusted generator measurements into one parcel per requested unit."""
    parcel = {
        "length": str(length_in),
        "width": str(width_in),
        "height": str(height_in),
        "distance_unit": "in",
        "weight": str(weight_lb),
        "mass_unit": "lb",
    }
    return [parcel.copy() for _ in range(generator_quantity)]


def _adapt_provider_messages(messages: Any) -> list[dict[str, str]]:
    """Validate normalized integration message objects for frontend output."""
    if not isinstance(messages, list):
        raise IntegrationResponseError(
            "Integration API returned invalid shipping messages."
        )
    normalized: list[dict[str, str]] = []
    for item in messages:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("source"), str)
            or not isinstance(item.get("message"), str)
        ):
            raise IntegrationResponseError(
                "Integration API returned invalid shipping messages."
            )
        normalized.append({"source": item["source"], "message": item["message"]})
    return normalized


def calculate_shipping_quote(
    origin_name: str,
    origin_street: str,
    origin_city: str,
    origin_state: str,
    origin_zip: str,
    customer_name: str,
    destination_street: str,
    destination_city: str,
    destination_state: str,
    destination_zip: str,
    generator_quantity: int,
    weight_lb: float,
    length_in: float,
    width_in: float,
    height_in: float,
    *,
    correlation_id: str | None = None,
    client: IntegrationAPIClient | None = None,
) -> dict[str, Any]:
    """Return the existing frontend quote contract through the integration API.

    Oversized generators return a freight-required business result without an
    HTTP integration call. Otherwise trusted generator measurements are expanded
    into parcels and the integration result is adapted to backend-owned wording.
    """
    if _calculate_length_plus_girth(length_in, width_in, height_in) > (
        MAX_PARCEL_LENGTH_PLUS_GIRTH_IN
    ):
        return {
            "success": False,
            "message": (
                "This generator exceeds the standard parcel size limit "
                "and requires a freight quote."
            ),
            "shippo_messages": [],
        }

    integration_client = client or IntegrationAPIClient()
    response = integration_client.shipping_quote(
        {
            "address_from": {
                "name": origin_name,
                "street1": origin_street,
                "city": origin_city,
                "state": origin_state.upper(),
                "zip": origin_zip,
                "country": "US",
            },
            "address_to": {
                "name": customer_name,
                "street1": destination_street,
                "city": destination_city,
                "state": destination_state.upper(),
                "zip": destination_zip,
                "country": "US",
            },
            "parcels": _build_parcels(
                generator_quantity,
                weight_lb,
                length_in,
                width_in,
                height_in,
            ),
        },
        correlation_id=correlation_id,
    )

    if response.get("success") is True:
        required_fields = {
            "carrier",
            "service",
            "amount",
            "currency",
            "estimated_days",
        }
        if not required_fields <= response.keys():
            raise IntegrationResponseError(
                "Integration API returned an invalid successful quote."
            )
        return {
            "success": True,
            "message": "Shipping rates available.",
            "carrier": response["carrier"],
            "service": response["service"],
            "amount": response["amount"],
            "currency": response["currency"],
            "estimated_days": response["estimated_days"],
        }

    if response.get("error_code") != "NO_RATES":
        raise IntegrationResponseError(
            "Integration API returned an unexpected shipping error result."
        )
    return {
        "success": False,
        "error_code": "NO_RATES",
        "message": "No shipping rate was available for the supplied shipment.",
        "shippo_messages": _adapt_provider_messages(
            response.get("shippo_messages", [])
        ),
    }
