"""Expose the backend's public SQLAlchemy domain model types.

Database engine and session setup intentionally live in ``model.database`` so
importing domain types alone does not initialize local persistence.

Importing this package registers Customer, HydrogenGenerator, and their asset
association with the shared ``Base.metadata`` registry. API and service code
may import domain classes from here without depending on database internals.
"""

from model.base_class import Base
from model.customer import Customer
from model.customer_generator_asset import CustomerGeneratorAsset
from model.hydrogen_generator import HydrogenGenerator

__all__ = [
    "Base",
    "Customer",
    "CustomerGeneratorAsset",
    "HydrogenGenerator",
]