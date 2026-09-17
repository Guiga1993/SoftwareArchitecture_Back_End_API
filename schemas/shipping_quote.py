"""Define request and response contracts for shipping quote operations.

The request schema validates caller-owned origin and destination addresses,
generator selection, and quantity before the route loads trusted measurements.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Quote Request Contract
# =============================================================================

class ShippingQuoteSchema(BaseModel):
    """Validate shipment parties, US addresses, and generator selection.

    The route combines these user-supplied values with trusted dimensions and
    weight loaded from the selected generator record before calling the
    internal integration API.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_name": "Origin Company",
                "origin_street": "123 Origin Street",
                "origin_city": "Torrance",
                "origin_state": "CA",
                "origin_zip": "90504",
                "customer_name": "Customer Company",
                "destination_street": "456 Destination Street",
                "destination_city": "Atlanta",
                "destination_state": "GA",
                "destination_zip": "30301",
                "generator_id": 6,
                "generator_quantity": 1,
            }
        }
    )

    origin_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Sender or origin company name.",
    )

    customer_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Recipient or destination company name.",
    )

    origin_street: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Origin street address.",
    )

    origin_city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Origin city.",
    )

    origin_state: str = Field(
        ...,
        pattern=r"^[A-Za-z]{2}$",
        description="Two-letter origin state code.",
    )

    origin_zip: str = Field(
        ...,
        pattern=r"^\d{5}(?:-\d{4})?$",
        description="Origin ZIP code.",
    )

    destination_street: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Destination street address.",
    )

    destination_city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Destination city.",
    )

    destination_state: str = Field(
        ...,
        pattern=r"^[A-Za-z]{2}$",
        description="Two-letter destination state code.",
    )

    destination_zip: str = Field(
        ...,
        pattern=r"^\d{5}(?:-\d{4})?$",
        description="Destination ZIP code.",
    )

    generator_id: int = Field(
        ...,
        gt=0,
        description="Stored hydrogen generator ID.",
    )

    generator_quantity: int = Field(
        ...,
        gt=0,
        le=100,
        description="Number of generators in the combined shipment.",
    )

    @field_validator(
        "origin_name",
        "origin_street",
        "origin_city",
        "origin_zip",
        "customer_name",
        "destination_street",
        "destination_city",
        "destination_zip",
        mode="before",
    )
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        """Trim required text so whitespace-only input fails length validation."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("origin_state", "destination_state", mode="before")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        """Trim and uppercase state codes at the backend request boundary."""
        return value.strip().upper() if isinstance(value, str) else value


# =============================================================================
# Quote Response Contract
# =============================================================================

class ShippingProviderMessageSchema(BaseModel):
    """Represent one normalized provider message without raw response fields."""

    source: str
    message: str


class ShippingQuoteResponseSchema(BaseModel):
    """Represent either a selected rate or a no-rate result from Shippo.

    Carrier fields are populated only when ``success`` is true. On a no-rate
    result they remain ``None`` and ``shippo_messages`` contains provider details.
    ``default_factory`` gives each response its own message list.
    """

    success: bool
    message: str
    error_code: Literal["NO_RATES"] | None = None
    carrier: str | None = None
    service: str | None = None
    amount: str | None = None
    currency: str | None = None
    estimated_days: int | None = None
    shippo_messages: list[ShippingProviderMessageSchema] = Field(default_factory=list)