"""Define the single declarative metadata registry used by every ORM model.

All mapped classes must inherit from ``Base`` so table creation, inspection,
and future migration tooling operate on one consistent metadata collection.
This module intentionally contains no engine or session configuration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Own shared metadata used for table creation and schema inspection.

    SQLAlchemy supplies mapping behavior through ``DeclarativeBase``; domain
    models only need to inherit this class and declare their table columns.
    """