"""Map customer identity and contact information to the ``customers`` table.

This module owns database column names, sizes, nullability, and uniqueness for
customers. Request formatting and business-friendly validation messages remain
in ``schemas.customer`` and API route handlers.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from model.base_class import Base


CUSTOMER_NAME_MAX_LENGTH = 150
CUSTOMER_EMAIL_MAX_LENGTH = 100
CUSTOMER_TAX_ID_MAX_LENGTH = 20


# =============================================================================
# Customer Mapping
# =============================================================================

class Customer(Base):
    """Persist one customer's identity, email address, and fiscal identifier.

    Email and Tax ID uniqueness are enforced by the database. The API also
    performs pre-insert checks to provide clearer conflict messages.
    """

    __tablename__ = "customers"

    # Python-facing IDs differ from the legacy database primary-key names.
    customer_id: Mapped[int] = mapped_column("pk_customer", Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(CUSTOMER_NAME_MAX_LENGTH), nullable=False)
    # Database uniqueness remains the final protection against concurrent writes.
    email: Mapped[str] = mapped_column(
        String(CUSTOMER_EMAIL_MAX_LENGTH), unique=True, nullable=False
    )
    tx_id: Mapped[str] = mapped_column(
        String(CUSTOMER_TAX_ID_MAX_LENGTH), unique=True, nullable=False
    )

    def __init__(self, name: str, email: str, tx_id: str) -> None:
        """Create a new Customer instance.

        Args:
            name: customer's full name.
            email: customer's email address.
            tx_id: customer's fiscal identifier (format 000-00-0000).

        Note:
            The database assigns ``customer_id`` when the session flushes.
        """
        self.name = name
        self.email = email
        self.tx_id = tx_id