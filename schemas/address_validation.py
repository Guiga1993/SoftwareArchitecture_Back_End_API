"""Define request and response contracts for address validation operations.

The request describes one US postal address submitted by an API consumer. The
response mirrors the stable business dictionary returned by
``services.address_validation_service``.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AddressValidationSchema(BaseModel):
    """Validate and normalize the JSON body accepted by `/validate-address`."""

    customer_name: str = Field(min_length=2, max_length=150)
    street1: str = Field(min_length=3, max_length=150)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(pattern=r"^[A-Za-z]{2}$")
    zip_code: str = Field(pattern=r"^\d{5}(?:-\d{4})?$")

    @field_validator("customer_name", "street1", "city")
    @classmethod
    def trim_text_fields(cls, value: str) -> str:
        """Trim surrounding whitespace before the service builds its payload."""
        return value.strip()

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        """Normalize the accepted two-letter state code to uppercase."""
        return value.upper()


class AddressValidationResponseSchema(BaseModel):
    """Describe Shippo's normalized address assessment returned by the API."""

    success: bool
    valid: bool
    normalized_zip: str | None = None
    is_residential: bool | None = None
    # Shippo currently returns message objects; Any preserves provider details.
    messages: list[Any] = Field(default_factory=list)