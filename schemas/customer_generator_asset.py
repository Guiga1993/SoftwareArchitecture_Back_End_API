"""Validate and serialize customer-generator relationship API data.

This module defines contracts for creating, updating, locating, listing, and
deleting relationship records. Existence of referenced customers and generators
is a route/service concern; these schemas validate identifier and quantity shape.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Shared Relationship Constraints
# =============================================================================

# Keep this limit synchronized with the relationship quantity input in the frontend.
MAX_GENERATOR_QTD = 10_000


# =============================================================================
# Input Contract
# =============================================================================

class CustomerGeneratorAssetSchema(BaseModel):
    """Validate editable relationship fields and positive foreign-key IDs.

    Omitting ``installation_date`` lets the model default it during creation and
    tells the PUT route to preserve the existing date during an update.
    """

    customer_id: int = Field(gt=0)
    generator_id: int = Field(gt=0)
    generator_qtd: int = Field(gt=0, le=MAX_GENERATOR_QTD)
    installation_date: datetime | None = None


# =============================================================================
# Query Contract
# =============================================================================

class CustomerGeneratorAssetSearchSchema(BaseModel):
    """Identify one relationship for GET, PUT, or DELETE by positive asset ID."""

    asset_id: int = Field(default=1, gt=0)


# =============================================================================
# Response Contracts
# =============================================================================

class CustomerGeneratorAssetViewSchema(BaseModel):
    """Describe one relationship and its persisted installation timestamp."""

    asset_id: int
    customer_id: int
    generator_id: int
    generator_qtd: int
    installation_date: datetime


class CustomerGeneratorAssetListSchema(BaseModel):
    """Wrap relationship items returned by the collection route."""

    assets: list[CustomerGeneratorAssetViewSchema]


class CustomerGeneratorAssetDeleteSchema(BaseModel):
    """Describe a successful relationship deletion confirmation."""

    message: str
    asset_id: int


# =============================================================================
# Serialization Helpers
# =============================================================================

def get_asset(asset: Any) -> dict[str, Any]:
    """Serialize one relationship ORM object into its public response shape.

    Args:
        asset: Object exposing mapped relationship attributes.

    Returns:
        A dictionary matching ``CustomerGeneratorAssetViewSchema``.
    """
    return {
        "asset_id": asset.asset_id,
        "customer_id": asset.customer_id,
        "generator_id": asset.generator_id,
        "generator_qtd": asset.generator_qtd,
        "installation_date": asset.installation_date,
    }


def get_assets(assets: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """Serialize relationship objects using the canonical item serializer.

    Returns:
        A collection wrapper matching ``CustomerGeneratorAssetListSchema``.
    """
    return {"assets": [get_asset(asset) for asset in assets]}