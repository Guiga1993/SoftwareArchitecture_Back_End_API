"""Map customer-generator ownership links to the association table.

Each row connects an existing customer and generator, records the assigned
quantity, and stores the installation timestamp. Route handlers validate that
referenced records exist; foreign keys preserve relational integrity.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from model.base_class import Base


# =============================================================================
# Customer-Generator Association Mapping
# =============================================================================

class CustomerGeneratorAsset(Base):
    """Persist quantity and installation date for one customer-generator link.

    This explicit association model carries relationship data that cannot live
    on either parent table, unlike a simple many-to-many join table.
    """

    __tablename__ = "customer_generator_assets"

    # Database primary-key names are retained for compatibility with existing data.
    asset_id: Mapped[int] = mapped_column("pk_asset", Integer, primary_key=True)
    # Routes validate references explicitly; these constraints protect DB integrity.
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.pk_customer"), nullable=False
    )
    generator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hydrogen_generators.pk_generator"), nullable=False
    )
    generator_qtd: Mapped[int] = mapped_column(Integer, nullable=False)
    # Pass the callable, not datetime.now(), so each inserted row gets its own time.
    installation_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    def __init__(
        self,
        customer_id: int,
        generator_id: int,
        generator_qtd: int,
        installation_date: datetime | None = None,
    ) -> None:
        """Create a new link between a customer and a hydrogen generator.

        Args:
            customer_id: ID of the linked customer.
            generator_id: ID of the linked generator.
            generator_qtd: number of generator units in this link.
            installation_date: date the generators were installed; when omitted,
                SQLAlchemy applies the current time during insertion.

        Note:
            Foreign-key existence is checked when the row is persisted, not
            while this Python object is constructed.
        """
        self.customer_id = customer_id
        self.generator_id = generator_id
        self.generator_qtd = generator_qtd

        # Leave this unset when omitted so SQLAlchemy applies its column default.
        if installation_date is not None:
            self.installation_date = installation_date
