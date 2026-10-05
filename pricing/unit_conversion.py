from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class ConversionResult:
    """
    Represents a converted construction quantity.

    quantity is the converted quantity.
    unit is the resulting unit.
    purchase_quantity is the number of whole purchasing units
    required when the material is purchased in discrete units.
    """

    quantity: float
    unit: str
    purchase_quantity: int


# ============================================================
# BASIC VOLUME CONVERSIONS
# ============================================================


def cubic_metres_to_litres(volume_m3: float) -> float:
    """
    Convert cubic metres to litres.

    1 m³ = 1,000 litres.
    """

    if volume_m3 < 0:
        raise ValueError(
            "Volume cannot be negative."
        )

    return volume_m3 * 1000.0


def litres_to_cubic_metres(litres: float) -> float:
    """
    Convert litres to cubic metres.

    1,000 litres = 1 m³.
    """

    if litres < 0:
        raise ValueError(
            "Litres cannot be negative."
        )

    return litres / 1000.0


# ============================================================
# WATER
# ============================================================


WATER_LOAD_LITRES = 10_000.0


def water_loads_required(
    volume_m3: float,
) -> ConversionResult:
    """
    Convert construction water from cubic metres to
    10,000-litre purchasing/delivery loads.

    Example:

        20 m³
        = 20,000 litres
        = 2 loads
    """

    if volume_m3 < 0:
        raise ValueError(
            "Water volume cannot be negative."
        )

    litres = cubic_metres_to_litres(
        volume_m3
    )

    loads = ceil(
        litres / WATER_LOAD_LITRES
    )

    return ConversionResult(
        quantity=litres,
        unit="litres",
        purchase_quantity=loads,
    )


# ============================================================
# CEMENT
# ============================================================


@dataclass(frozen=True)
class CementConversion:
    """
    Defines the conversion assumptions used to convert
    cement volume into 50 kg bags.

    cement_density_kg_per_m3 must be supplied explicitly
    because the density assumption is a technical parameter
    that may be changed later.
    """

    cement_density_kg_per_m3: float

    bag_mass_kg: float = 50.0

    def __post_init__(self) -> None:

        if self.cement_density_kg_per_m3 <= 0:
            raise ValueError(
                "Cement density must be greater than zero."
            )

        if self.bag_mass_kg <= 0:
            raise ValueError(
                "Cement bag mass must be greater than zero."
            )


def cement_bags_required(
    volume_m3: float,
    conversion: CementConversion,
) -> ConversionResult:
    """
    Convert cement volume into kilograms and whole
    50 kg cement bags.

    The conversion uses the explicitly supplied density
    assumption.
    """

    if volume_m3 < 0:
        raise ValueError(
            "Cement volume cannot be negative."
        )

    mass_kg = (
        volume_m3
        * conversion.cement_density_kg_per_m3
    )

    bags = ceil(
        mass_kg / conversion.bag_mass_kg
    )

    return ConversionResult(
        quantity=mass_kg,
        unit="kg",
        purchase_quantity=bags,
    )


# ============================================================
# DISCRETE MATERIAL QUANTITIES
# ============================================================


def whole_units_required(
    quantity: float,
) -> int:
    """
    Round a discrete material quantity upward to the next
    whole purchasing unit.

    Example:

        16854.2 bricks
        → 16855 bricks
    """

    if quantity < 0:
        raise ValueError(
            "Quantity cannot be negative."
        )

    return ceil(quantity)