from math import ceil

from .models import MaterialQuantity, MasonryParameters


def calculate_bricks_required(
    wall_area_m2: float,
    parameters: MasonryParameters,
) -> MaterialQuantity:
    """
    Calculate the number of brick units required for a wall.

    The face area of the brick determines the number of bricks
    required per square metre. The actual wall thickness is
    used later when calculating the brick volume and mortar.

    Effective brick face dimensions include the mortar joint.
    """

    if wall_area_m2 < 0:
        raise ValueError(
            "Wall area cannot be negative."
        )

    effective_length_m = (
        parameters.unit_length_m
        + parameters.mortar_joint_thickness_m
    )

    effective_height_m = (
        parameters.unit_height_m
        + parameters.mortar_joint_thickness_m
    )

    area_per_unit_m2 = (
        effective_length_m
        * effective_height_m
    )

    base_quantity = (
        wall_area_m2
        / area_per_unit_m2
    )

    return MaterialQuantity(
        material_name="Standard brick",
        quantity=base_quantity,
        unit="units",
        wastage_percentage=parameters.wastage_percentage,
    )


def calculate_bricks_with_wastage(
    wall_area_m2: float,
    parameters: MasonryParameters,
) -> int:
    """
    Calculate the final whole-number brick quantity
    including the configured wastage percentage.
    """

    material_quantity = calculate_bricks_required(
        wall_area_m2=wall_area_m2,
        parameters=parameters,
    )

    return ceil(
        material_quantity.quantity_with_wastage
    )


def calculate_mortar_required(
    masonry_volume_m3: float,
    brick_quantity: float,
    parameters: MasonryParameters,
) -> MaterialQuantity:
    """
    Calculate mortar volume for the actual wall thickness.

    The wall volume represents the complete masonry volume.

    The brick quantity is adjusted according to the number of
    brick layers required to construct the selected wall thickness.

    For a wall thickness of 200 mm and a brick thickness of
    110 mm, two brick widths are required.

    The calculation therefore uses:

        brick_widths =
            ceil(
                wall_thickness / brick_thickness
            )

        effective_brick_volume =
            brick_quantity
            × brick_length
            × brick_height
            × brick_widths
    """

    if masonry_volume_m3 < 0:
        raise ValueError(
            "Masonry volume cannot be negative."
        )

    if brick_quantity < 0:
        raise ValueError(
            "Brick quantity cannot be negative."
        )

    brick_widths = ceil(
        parameters.wall_thickness_m
        / parameters.unit_thickness_m
    )

    brick_volume_m3 = (
        parameters.unit_length_m
        * parameters.unit_height_m
        * parameters.unit_thickness_m
    )

    total_brick_volume_m3 = (
        brick_quantity
        * brick_volume_m3
        * brick_widths
    )

    mortar_volume_m3 = (
        masonry_volume_m3
        - total_brick_volume_m3
    )

    if mortar_volume_m3 < 0:
        mortar_volume_m3 = 0.0

    return MaterialQuantity(
        material_name="Mortar",
        quantity=mortar_volume_m3,
        unit="m3",
        wastage_percentage=parameters.wastage_percentage,
    )