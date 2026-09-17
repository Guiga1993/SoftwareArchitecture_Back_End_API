"""Configure local persistence and initialize the SQLite schema.

Importing this module creates the database directory, creates missing mapped
tables, and applies additive compatibility updates required by older local
development databases. It does not insert seed or application records.
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from model.base_class import Base


# =============================================================================
# Database Location and Legacy Defaults
# =============================================================================

DATABASE_DIR = Path(__file__).resolve().parents[1] / "database"
DATABASE_PATH = DATABASE_DIR / "db.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Existing rows receive these neutral shipping values only when upgrading a
# database created before generator shipping measurements were introduced.
LEGACY_GENERATOR_SHIPPING_DEFAULTS = {
    "length_in": 48.0,
    "width_in": 40.0,
    "height_in": 60.0,
    "weight_lb": 12.0,
}

# Resolve storage from this module instead of the process working directory.
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Engine and Session Factory
# =============================================================================

engine = create_engine(DATABASE_URL, echo=False)
session_factory = sessionmaker(bind=engine)


# =============================================================================
# Schema Initialization
# =============================================================================

def initialize_database() -> None:
    """Create missing tables and idempotently upgrade legacy generator columns.

    The function first creates every table registered with ``Base.metadata``.
    It then inspects ``hydrogen_generators`` and adds shipping columns absent
    from older development databases. Repeated calls are safe because existing
    tables and columns are left unchanged.

    Side effects:
        Creates or modifies the project-local SQLite schema. It never inserts,
        updates, or deletes application records.
    """
    Base.metadata.create_all(engine)

    # Existing development databases predate the shipping measurement columns.
    # This compatibility step is intentionally additive and safe to run repeatedly.
    generator_columns = {
        column["name"]
        for column in inspect(engine).get_columns("hydrogen_generators")
    }
    with engine.begin() as connection:
        for column_name, default_value in LEGACY_GENERATOR_SHIPPING_DEFAULTS.items():
            if column_name not in generator_columns:
                connection.execute(text(
                    f"ALTER TABLE hydrogen_generators ADD COLUMN {column_name} "
                    f"FLOAT NOT NULL DEFAULT {default_value}"
                ))


# Application imports rely on the database being ready before route handling.
initialize_database()


__all__ = ["engine", "initialize_database", "session_factory"]