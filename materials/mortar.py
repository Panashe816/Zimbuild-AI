from dataclasses import dataclass

from .models import MaterialQuantity


@dataclass(frozen=True)
class MortarMix:
    """
    Defines the proportions of materials in a mortar mix.

    Example:
        1 : 6
        cement : sand
    """

    cement_parts: float
    sand_parts: float

    def __post_init__(self) -> None:
        if self.cement_parts <= 0:
            raise ValueError(
                "Cement parts must be greater than zero."
            )

        if self.sand_parts <= 0:
            raise ValueError(
                "Sand parts must be greater than zero."
            )

    @property
    def total_parts(self) -> float:
        return (
            self.cement_parts
            + self.sand_parts
        )


@dataclass(frozen=True)
class MortarConversionParameters:
    """
    Technical assumptions used to convert finished mortar
    volume into dry constituent quantities.

    dry_volume_factor:
        Converts finished/wet mortar volume into the
        approximate dry ingredient volume required.

    cement_density_kg_per_m3:
        Bulk density assumption used to convert cement
        volume into kilograms.

    cement_bag_mass_kg:
        Standard cement bag size.
    """

    dry_volume_factor: float = 1.33

    cement_density_kg_per_m3: float = 1400.0

    cement_bag_mass_kg: float = 50.0

    wastage_percentage: float = 5.0

    def __post_init__(self) -> None:

        if self.dry_volume_factor <= 0:
            raise ValueError(
                "Dry volume factor must be greater than zero."
            )

        if self.cement_density_kg_per_m3 <= 0:
            raise ValueError(
                "Cement density must be greater than zero."
            )

        if self.cement_bag_mass_kg <= 0:
            raise ValueError(
                "Cement bag mass must be greater than zero."
            )

        if self.wastage_percentage < 0:
            raise ValueError(
                "Wastage percentage cannot be negative."
            )


DEFAULT_MORTAR_MIX = MortarMix(
    cement_parts=1.0,
    sand_parts=6.0,
)


DEFAULT_MORTAR_CONVERSION = MortarConversionParameters()


def calculate_mortar_materials(
    mortar_volume_m3: float,
    mix: MortarMix = DEFAULT_MORTAR_MIX,
    conversion: MortarConversionParameters =
        DEFAULT_MORTAR_CONVERSION,
) -> tuple[MaterialQuantity, MaterialQuantity]:
    """
    Calculate cement and sand quantities required for a
    specified finished mortar volume.

    The calculation first converts finished mortar volume
    to dry ingredient volume.

    The dry ingredient volume is then divided according
    to the selected cement:sand mix ratio.
    """

    if mortar_volume_m3 < 0:
        raise ValueError(
            "Mortar volume cannot be negative."
        )

    dry_volume_m3 = (
        mortar_volume_m3
        * conversion.dry_volume_factor
    )

    cement_fraction = (
        mix.cement_parts
        / mix.total_parts
    )

    sand_fraction = (
        mix.sand_parts
        / mix.total_parts
    )

    cement_volume_m3 = (
        dry_volume_m3
        * cement_fraction
    )

    sand_volume_m3 = (
        dry_volume_m3
        * sand_fraction
    )

    cement = MaterialQuantity(
        material_name="Cement",
        quantity=cement_volume_m3,
        unit="m3",
        wastage_percentage=(
            conversion.wastage_percentage
        ),
    )

    sand = MaterialQuantity(
        material_name="Building sand",
        quantity=sand_volume_m3,
        unit="m3",
        wastage_percentage=(
            conversion.wastage_percentage
        ),
    )

    return cement, sand


def calculate_cement_bags(
    cement_volume_m3: float,
    conversion: MortarConversionParameters =
        DEFAULT_MORTAR_CONVERSION,
) -> int:
    """
    Convert cement volume into whole 50 kg bags.

    The density assumption is explicit and configurable.
    Wastage is included before rounding to whole bags.
    """

    if cement_volume_m3 < 0:
        raise ValueError(
            "Cement volume cannot be negative."
        )

    cement_volume_with_wastage = (
        cement_volume_m3
        * (
            1
            + conversion.wastage_percentage / 100
        )
    )

    cement_mass_kg = (
        cement_volume_with_wastage
        * conversion.cement_density_kg_per_m3
    )

    from math import ceil

    return ceil(
        cement_mass_kg
        / conversion.cement_bag_mass_kg
    )