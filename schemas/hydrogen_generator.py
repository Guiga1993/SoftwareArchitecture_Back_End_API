"""Validate generator API inputs and serialize generator response data.

The module owns current and legacy serial conventions, allowed commercial and
stack categories, technical ranges, parcel limits, query normalization, and
the response shapes used by generator CRUD routes.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Shared Generator Constraints
# =============================================================================

# Literals are part of the frontend/backend contract and match the form options.
AcquisitionType = Literal["Leasing", "Renting", "Direct Sales"]
StackType = Literal["PEMFC", "Alcaline", "SOFC", "AEMFC", "Other/Personalized"]
SERIAL_NUMBER_REGEX = r"GEN-\d{4}"
# GENSET values remain readable for databases created before GEN became standard.
SERIAL_LOOKUP_REGEX = r"(?:GEN-\d{4}|GENSET-\d{4})"
MAX_PARCEL_SIDE_IN = 108
MAX_PARCEL_LENGTH_PLUS_GIRTH_IN = 165
MAX_PARCEL_WEIGHT_LB = 150


# =============================================================================
# Input Contract
# =============================================================================

class HydrogenGeneratorCreateSchema(BaseModel):
    """Validate fields shared by generator POST and PUT operations.

    Pydantic handles category and numeric bounds. Custom validators normalize
    serial numbers and enforce the carrier's combined length-plus-girth limit
    after all three dimensions have been parsed.
    """

    serial_number: str
    acquisition_type: AcquisitionType
    stack_type: StackType
    number_of_cells: int = Field(gt=0, le=5000)
    stack_voltage: float = Field(gt=0, le=2000)
    current_density: float = Field(gt=0, le=5000)
    # Dimensions are inches and weight is pounds throughout the API.
    length_in: float = Field(gt=0, le=MAX_PARCEL_SIDE_IN)
    width_in: float = Field(gt=0, le=MAX_PARCEL_SIDE_IN)
    height_in: float = Field(gt=0, le=MAX_PARCEL_SIDE_IN)
    weight_lb: float = Field(gt=0, le=MAX_PARCEL_WEIGHT_LB)

    @field_validator("serial_number")
    @classmethod
    def validate_serial_number(cls, value: str) -> str:
        """Normalize and validate a serial using the current GEN-0000 convention.

        Args:
            value: Raw generator serial supplied by the API client.

        Returns:
            The trimmed, uppercase serial used for persistence and lookup.
        """
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Serial number cannot be empty.")
        if not re.fullmatch(SERIAL_NUMBER_REGEX, normalized):
            raise ValueError(
                "Serial number must follow the format GEN-0000 (e.g., GEN-0001)."
            )
        if len(normalized) > 50:
            raise ValueError("Serial number must contain at most 50 characters.")
        return normalized

    @model_validator(mode="after")
    def validate_parcel_dimensions(self):
        """Enforce carrier length-plus-girth after all dimensions are parsed.

        Returns:
            This validated schema instance when its parcel remains within the
            standard carrier limit.
        """
        # Carrier length is the longest side, regardless of input field ordering.
        dimensions = sorted(
            (self.length_in, self.width_in, self.height_in),
            reverse=True,
        )
        length_plus_girth = dimensions[0] + 2 * (dimensions[1] + dimensions[2])
        if length_plus_girth > MAX_PARCEL_LENGTH_PLUS_GIRTH_IN:
            raise ValueError(
                "Generator dimensions exceed the 165 in parcel length-plus-girth limit."
            )
        return self


# =============================================================================
# Query Contract
# =============================================================================

class HydrogenGeneratorSearchSchema(BaseModel):
    """Normalize current and legacy serials used by GET, PUT, and DELETE routes."""

    serial_number: str = Field(default="GEN-0001")

    @field_validator("serial_number")
    @classmethod
    def validate_search_serial_number(cls, value: str) -> str:
        """Normalize a lookup serial and accept current or legacy formats.

        Args:
            value: Raw serial supplied as a query parameter.

        Returns:
            The trimmed, uppercase serial used by database filters.
        """
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Serial number cannot be empty.")
        if not re.fullmatch(SERIAL_LOOKUP_REGEX, normalized):
            raise ValueError(
                "Serial number must follow the format GEN-0000 (e.g., GEN-0001)."
            )
        if len(normalized) > 50:
            raise ValueError("Serial number must contain at most 50 characters.")
        return normalized


# =============================================================================
# Response Contracts
# =============================================================================

class HydrogenGeneratorViewSchema(BaseModel):
    """Describe one generator's identity, operating data, and shipping values."""

    generator_id: int
    serial_number: str
    acquisition_type: str
    stack_type: str
    number_of_cells: int
    stack_voltage: float
    current_density: float
    length_in: float
    width_in: float
    height_in: float
    weight_lb: float


class HydrogenGeneratorListSchema(BaseModel):
    """Wrap generator items returned by the generator collection route."""

    generators: list[HydrogenGeneratorViewSchema]


class HydrogenGeneratorDeleteSchema(BaseModel):
    """Describe a successful generator deletion confirmation."""

    message: str
    serial_number: str


# =============================================================================
# Serialization Helpers
# =============================================================================

def get_hydrogen_generator(generator: Any) -> dict[str, Any]:
    """Serialize one generator ORM object into its public response shape.

    Args:
        generator: Object exposing all mapped generator attributes.

    Returns:
        A JSON-compatible dictionary matching ``HydrogenGeneratorViewSchema``.
    """
    return {
        "generator_id": generator.generator_id,
        "serial_number": generator.serial_number,
        "acquisition_type": generator.acquisition_type,
        "stack_type": generator.stack_type,
        "number_of_cells": generator.number_of_cells,
        "stack_voltage": generator.stack_voltage,
        "current_density": generator.current_density,
        "length_in": generator.length_in,
        "width_in": generator.width_in,
        "height_in": generator.height_in,
        "weight_lb": generator.weight_lb,
    }


def get_hydrogen_generators(generators: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """Serialize generator objects using the canonical item serializer.

    Returns:
        A collection wrapper matching ``HydrogenGeneratorListSchema``.
    """
    return {
        "generators": [get_hydrogen_generator(generator) for generator in generators]
    }