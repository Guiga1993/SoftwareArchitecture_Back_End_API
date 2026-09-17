"""Validate customer API inputs and serialize customer response data.

The schemas in this module support customer create, update, search, list, and
delete routes. Validators normalize user input before route handlers construct
ORM objects, while serializer helpers keep response fields consistent.
"""

import re
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator


# =============================================================================
# Shared Customer Constraints
# =============================================================================

# Keep input length aligned with model.customer.CUSTOMER_NAME_MAX_LENGTH.
NonEmptyName = Annotated[str, StringConstraints(min_length=2, max_length=150)]
TAX_ID_REGEX = r"\d{3}-\d{2}-\d{4}"


# =============================================================================
# Input Contract
# =============================================================================

class CustomerSchema(BaseModel):
    """Validate editable fields shared by customer POST and PUT operations.

    Pydantic validates the email address and declared lengths. Custom validators
    trim the customer name and enforce the project's formatted Tax ID contract.
    """

    name: NonEmptyName
    email: EmailStr
    tx_id: str = Field(min_length=11, max_length=11)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Trim surrounding whitespace and reject an empty or one-letter name.

        Args:
            value: Raw customer name supplied by the API client.

        Returns:
            The normalized customer name used by the route and ORM model.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be empty.")
        if len(normalized) < 2:
            raise ValueError("Name must contain at least 2 characters.")
        return normalized

    @field_validator("tx_id")
    @classmethod
    def validate_tx_id(cls, value: str) -> str:
        """Validate and return a Tax ID in the required 000-00-0000 format.

        Args:
            value: Tax ID text supplied by the API client.

        Returns:
            The unchanged Tax ID after successful format validation.
        """
        if not re.fullmatch(TAX_ID_REGEX, value):
            raise ValueError("Tax ID must follow the format 000-00-0000.")
        return value


# =============================================================================
# Query Contract
# =============================================================================

class CustomerSearchSchema(BaseModel):
    """Identify one customer for GET, PUT, or DELETE by positive database ID."""

    customer_id: int = Field(default=1, gt=0)


# =============================================================================
# Response Contracts
# =============================================================================

class CustomerViewSchema(BaseModel):
    """Describe the public customer representation returned by write/read routes."""

    customer_id: int
    name: str
    email: str
    tx_id: str


class CustomerListSchema(BaseModel):
    """Wrap customer items returned by the customer collection route."""

    customers: list[CustomerViewSchema]


class CustomerDeleteSchema(BaseModel):
    """Describe a successful customer deletion confirmation."""

    message: str
    customer_id: int


# =============================================================================
# Serialization Helpers
# =============================================================================

# Helpers keep SQLAlchemy implementation details out of route response bodies.
def get_customer(customer: Any) -> dict[str, Any]:
    """Serialize one customer ORM object into its public response shape.

    Args:
        customer: Object exposing the mapped customer attributes.

    Returns:
        A JSON-compatible dictionary matching ``CustomerViewSchema``.
    """
    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "email": customer.email,
        "tx_id": customer.tx_id,
    }


def get_customers(customers: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """Serialize customer objects using the canonical item serializer.

    Returns:
        A collection wrapper matching ``CustomerListSchema``.
    """
    return {"customers": [get_customer(customer) for customer in customers]}