"""
ZimBuild AI - Building Quantity Service

Combines:
    1. Geometry detected from the uploaded architectural plan
    2. User-supplied construction parameters
    3. Derived construction quantities

The interactive input in this file is a prototype of the
same information-entry process that will later be implemented
in the ZimBuild AI frontend.

Roofing is intentionally excluded.
"""

from dataclasses import dataclass
from typing import Optional

from .construction_parameters_service import (
    ConstructionParameters,
    build_construction_parameters,
)


# ============================================================
# BUILDING QUANTITY RESULT
# ============================================================

@dataclass
class BuildingQuantities:

    # --------------------------------------------------------
    # Building geometry
    # --------------------------------------------------------

    floor_area_m2: float

    wall_count: int
    total_wall_length_m: float
    external_wall_length_m: float
    internal_wall_length_m: float

    door_count: int
    window_count: int
    room_count: int

    total_door_opening_width_m: float
    total_window_opening_width_m: float

    # --------------------------------------------------------
    # Construction specifications
    # --------------------------------------------------------

    wall_height_m: Optional[float]
    foundation_width_m: Optional[float]
    foundation_depth_m: Optional[float]
    slab_thickness_m: Optional[float]
    hardcore_depth_m: Optional[float]

    # --------------------------------------------------------
    # Derived quantities
    # --------------------------------------------------------

    gross_wall_area_m2: Optional[float] = None
    foundation_volume_m3: Optional[float] = None
    slab_concrete_volume_m3: Optional[float] = None
    hardcore_volume_m3: Optional[float] = None

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    ready_for_material_calculation: bool = False

    missing_parameters: list = None


# ============================================================
# USER INPUT
# ============================================================

def ask_for_missing_parameters(
    parameters: ConstructionParameters,
) -> ConstructionParameters:
    """
    Ask the user to manually enter construction parameters
    that were not detected from the architectural plan.

    This interactive process will later be replaced by
    frontend form inputs.
    """

    print()
    print("=" * 70)
    print("CONSTRUCTION INFORMATION REQUIRED FROM USER")
    print("=" * 70)

    print()
    print(
        "Some construction information could not be reliably "
        "detected from the architectural plan."
    )

    print(
        "Please enter the missing values below."
    )

    print()

    # --------------------------------------------------------
    # Wall height
    # --------------------------------------------------------

    if parameters.wall_height_m is None:

        print(
            "Wall height was not detected from the plan."
        )

        while True:
            try:
                value = float(
                    input("Enter wall height (m): ").strip()
                )

                if value <= 0:
                    print("Please enter a value greater than 0.")
                    continue

                parameters.wall_height_m = value
                break

            except ValueError:
                print(
                    "Invalid value. Please enter a number, "
                    "for example 2.7"
                )

    # --------------------------------------------------------
    # Foundation width
    # --------------------------------------------------------

    if parameters.foundation_width_m is None:

        print()
        print(
            "Foundation width was not detected from the plan."
        )

        while True:
            try:
                value = float(
                    input("Enter foundation width (m): ").strip()
                )

                if value <= 0:
                    print("Please enter a value greater than 0.")
                    continue

                parameters.foundation_width_m = value
                break

            except ValueError:
                print(
                    "Invalid value. Please enter a number, "
                    "for example 0.6"
                )

    # --------------------------------------------------------
    # Foundation depth
    # --------------------------------------------------------

    if parameters.foundation_depth_m is None:

        print()
        print(
            "Foundation depth was not detected from the plan."
        )

        while True:
            try:
                value = float(
                    input("Enter foundation depth (m): ").strip()
                )

                if value <= 0:
                    print("Please enter a value greater than 0.")
                    continue

                parameters.foundation_depth_m = value
                break

            except ValueError:
                print(
                    "Invalid value. Please enter a number, "
                    "for example 0.6"
                )

    # --------------------------------------------------------
    # Slab thickness
    # --------------------------------------------------------

    if parameters.slab_thickness_m is None:

        print()
        print(
            "Slab thickness was not detected from the plan."
        )

        while True:
            try:
                value = float(
                    input("Enter slab thickness (m): ").strip()
                )

                if value <= 0:
                    print("Please enter a value greater than 0.")
                    continue

                parameters.slab_thickness_m = value
                break

            except ValueError:
                print(
                    "Invalid value. Please enter a number, "
                    "for example 0.15"
                )

    # --------------------------------------------------------
    # Hardcore depth
    # --------------------------------------------------------

    if parameters.hardcore_depth_m is None:

        print()
        print(
            "Hardcore depth was not detected from the plan."
        )

        while True:
            try:
                value = float(
                    input("Enter hardcore depth (m): ").strip()
                )

                if value <= 0:
                    print("Please enter a value greater than 0.")
                    continue

                parameters.hardcore_depth_m = value
                break

            except ValueError:
                print(
                    "Invalid value. Please enter a number, "
                    "for example 0.15"
                )

    # --------------------------------------------------------
    # Clear missing parameter list
    # --------------------------------------------------------

    parameters.required_inputs = []

    return parameters


# ============================================================
# SAFE MULTIPLICATION
# ============================================================

def _multiply_if_complete(*values):

    if any(value is None for value in values):
        return None

    result = 1.0

    for value in values:
        result *= float(value)

    return result


# ============================================================
# BUILD QUANTITIES
# ============================================================

def calculate_building_quantities(
    parameters: ConstructionParameters,
) -> BuildingQuantities:

    # --------------------------------------------------------
    # Gross wall area
    # --------------------------------------------------------

    gross_wall_area = _multiply_if_complete(
        parameters.total_wall_length_m,
        parameters.wall_height_m,
    )

    # --------------------------------------------------------
    # Foundation volume
    # --------------------------------------------------------

    foundation_volume = _multiply_if_complete(
        parameters.total_wall_length_m,
        parameters.foundation_width_m,
        parameters.foundation_depth_m,
    )

    # --------------------------------------------------------
    # Slab concrete volume
    # --------------------------------------------------------

    slab_concrete_volume = _multiply_if_complete(
        parameters.floor_area_m2,
        parameters.slab_thickness_m,
    )

    # --------------------------------------------------------
    # Hardcore volume
    # --------------------------------------------------------

    hardcore_volume = _multiply_if_complete(
        parameters.floor_area_m2,
        parameters.hardcore_depth_m,
    )

    # --------------------------------------------------------
    # Check readiness
    # --------------------------------------------------------

    missing_parameters = []

    if parameters.wall_height_m is None:
        missing_parameters.append("wall_height_m")

    if parameters.foundation_width_m is None:
        missing_parameters.append("foundation_width_m")

    if parameters.foundation_depth_m is None:
        missing_parameters.append("foundation_depth_m")

    if parameters.slab_thickness_m is None:
        missing_parameters.append("slab_thickness_m")

    if parameters.hardcore_depth_m is None:
        missing_parameters.append("hardcore_depth_m")

    ready = len(missing_parameters) == 0

    return BuildingQuantities(

        floor_area_m2=parameters.floor_area_m2 or 0.0,

        wall_count=parameters.wall_count,

        total_wall_length_m=(
            parameters.total_wall_length_m
        ),

        external_wall_length_m=(
            parameters.external_wall_length_m
        ),

        internal_wall_length_m=(
            parameters.internal_wall_length_m
        ),

        door_count=parameters.door_count,

        window_count=parameters.window_count,

        room_count=parameters.room_count,

        total_door_opening_width_m=(
            parameters.total_door_opening_width_m
        ),

        total_window_opening_width_m=(
            parameters.total_window_opening_width_m
        ),

        wall_height_m=parameters.wall_height_m,

        foundation_width_m=(
            parameters.foundation_width_m
        ),

        foundation_depth_m=(
            parameters.foundation_depth_m
        ),

        slab_thickness_m=(
            parameters.slab_thickness_m
        ),

        hardcore_depth_m=(
            parameters.hardcore_depth_m
        ),

        gross_wall_area_m2=gross_wall_area,

        foundation_volume_m3=foundation_volume,

        slab_concrete_volume_m3=(
            slab_concrete_volume
        ),

        hardcore_volume_m3=hardcore_volume,

        ready_for_material_calculation=ready,

        missing_parameters=missing_parameters,
    )


# ============================================================
# REPORT
# ============================================================

def print_building_quantity_report(
    quantities: BuildingQuantities,
):

    print()
    print("=" * 70)
    print("ZIMBUILD AI - BUILDING QUANTITIES")
    print("=" * 70)

    print()
    print("FINAL BUILDING DATA")
    print("-" * 70)

    print(
        f"Floor area:              "
        f"{quantities.floor_area_m2:.3f} m²"
    )

    print(
        f"Wall count:              "
        f"{quantities.wall_count}"
    )

    print(
        f"Total wall length:       "
        f"{quantities.total_wall_length_m:.3f} m"
    )

    print(
        f"External wall length:    "
        f"{quantities.external_wall_length_m:.3f} m"
    )

    print(
        f"Internal wall length:    "
        f"{quantities.internal_wall_length_m:.3f} m"
    )

    print(
        f"Rooms:                   "
        f"{quantities.room_count}"
    )

    print(
        f"Doors:                   "
        f"{quantities.door_count}"
    )

    print(
        f"Windows:                 "
        f"{quantities.window_count}"
    )

    print(
        f"Door opening width:      "
        f"{quantities.total_door_opening_width_m:.3f} m"
    )

    print(
        f"Window opening width:    "
        f"{quantities.total_window_opening_width_m:.3f} m"
    )

    print()
    print("CONSTRUCTION PARAMETERS")
    print("-" * 70)

    print(
        f"Wall height:             "
        f"{quantities.wall_height_m:.3f} m"
    )

    print(
        f"Foundation width:        "
        f"{quantities.foundation_width_m:.3f} m"
    )

    print(
        f"Foundation depth:        "
        f"{quantities.foundation_depth_m:.3f} m"
    )

    print(
        f"Slab thickness:          "
        f"{quantities.slab_thickness_m:.3f} m"
    )

    print(
        f"Hardcore depth:          "
        f"{quantities.hardcore_depth_m:.3f} m"
    )

    print()
    print("DERIVED QUANTITIES")
    print("-" * 70)

    print(
        f"Gross wall area:         "
        f"{quantities.gross_wall_area_m2:.3f} m²"
    )

    print(
        f"Foundation volume:       "
        f"{quantities.foundation_volume_m3:.3f} m³"
    )

    print(
        f"Slab concrete volume:    "
        f"{quantities.slab_concrete_volume_m3:.3f} m³"
    )

    print(
        f"Hardcore volume:         "
        f"{quantities.hardcore_volume_m3:.3f} m³"
    )

    print()
    print("=" * 70)

    if quantities.ready_for_material_calculation:
        print(
            "STATUS: READY FOR MATERIAL CALCULATION"
        )
    else:
        print(
            "STATUS: ADDITIONAL PARAMETERS REQUIRED"
        )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load information detected from the architectural plan
    # --------------------------------------------------------

    parameters = build_construction_parameters()

    # --------------------------------------------------------
    # Ask user for anything the plan could not provide
    # --------------------------------------------------------

    parameters = ask_for_missing_parameters(
        parameters
    )

    # --------------------------------------------------------
    # Calculate building quantities
    # --------------------------------------------------------

    quantities = calculate_building_quantities(
        parameters
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print_building_quantity_report(
        quantities
    )


if __name__ == "__main__":
    main()