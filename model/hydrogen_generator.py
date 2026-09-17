"""Map technical and shipping data to the ``hydrogen_generators`` table.

This module owns persistent generator attributes and database constraints.
Allowed categories, numeric ranges, serial formatting, and parcel limits are
validated in ``schemas.hydrogen_generator`` before model construction.
"""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from model.base_class import Base


SERIAL_NUMBER_MAX_LENGTH = 50
ACQUISITION_TYPE_MAX_LENGTH = 20
STACK_TYPE_MAX_LENGTH = 50


# =============================================================================
# Hydrogen Generator Mapping
# =============================================================================

class HydrogenGenerator(Base):
    """Persist one generator's identity, operating data, and parcel dimensions.

    Shipping measurements use inches and pounds to match the Shippo payload.
    The unique serial number is the generator's external lookup identifier.
    """

    __tablename__ = "hydrogen_generators"

    # Python-facing IDs differ from the legacy database primary-key names.
    generator_id: Mapped[int] = mapped_column("pk_generator", Integer, primary_key=True)
    # Serial uniqueness is enforced here as a final guard for concurrent writes.
    serial_number: Mapped[str] = mapped_column(
        String(SERIAL_NUMBER_MAX_LENGTH), unique=True, nullable=False
    )
    acquisition_type: Mapped[str] = mapped_column(
        String(ACQUISITION_TYPE_MAX_LENGTH), nullable=False
    )
    stack_type: Mapped[str] = mapped_column(String(STACK_TYPE_MAX_LENGTH), nullable=False)
    number_of_cells: Mapped[int] = mapped_column(Integer, nullable=False)
    stack_voltage: Mapped[float] = mapped_column(Float, nullable=False)
    current_density: Mapped[float] = mapped_column(Float, nullable=False)
    # Shipping dimensions are inches and weight is pounds across the API contract.
    length_in: Mapped[float] = mapped_column(Float, nullable=False)
    width_in: Mapped[float] = mapped_column(Float, nullable=False)
    height_in: Mapped[float] = mapped_column(Float, nullable=False)
    weight_lb: Mapped[float] = mapped_column(Float, nullable=False)

    def __init__(
        self,
        serial_number: str,
        acquisition_type: str,
        stack_type: str,
        number_of_cells: int,
        stack_voltage: float,
        current_density: float,
        length_in: float,
        width_in: float,
        height_in: float,
        weight_lb: float,
    ) -> None:
        """Create a new HydrogenGenerator instance.

        Args:
            serial_number: unique identifier for the physical unit.
            acquisition_type: how the generator was acquired.
            stack_type: fuel-cell technology used.
            number_of_cells: cell count in the stack.
            stack_voltage: total voltage output (V).
            current_density: operating current density (A/cm²).
            length_in: packaged length in inches.
            width_in: packaged width in inches.
            height_in: packaged height in inches.
            weight_lb: packaged weight in pounds.

        Note:
            The database assigns ``generator_id`` when the session flushes.
        """
        self.serial_number = serial_number
        self.acquisition_type = acquisition_type
        self.stack_type = stack_type
        self.number_of_cells = number_of_cells
        self.stack_voltage = stack_voltage
        self.current_density = current_density
        self.length_in = length_in
        self.width_in = width_in
        self.height_in = height_in
        self.weight_lb = weight_lb