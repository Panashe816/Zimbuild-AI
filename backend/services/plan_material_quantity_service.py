"""
ZimBuild AI - Plan Material Quantity Service

Stage-based construction material estimation.

Stages:

    1. Foundation
    2. Walls
    3. Floor / Slab
    4. Reinforcement & Masonry Reinforcement
    5. Roofing - excluded

Stage 4 uses user-defined construction rules:

    Reinforcement runs around external walls
    Brick force interval
    Brick force on external walls
    Brick force on internal walls
    Reinforcement mesh required
    Mesh allowance
"""

from dataclasses import dataclass
from typing import List

from math import ceil

from .construction_parameters_service import (
    build_construction_parameters,
)

from .building_quantity_service import (
    ask_for_missing_parameters,
    calculate_building_quantities,
)


# ============================================================
# MATERIAL RESULT
# ============================================================

@dataclass
class CalculatedMaterial:

    material_name: str
    quantity: float
    unit: str
    basis: str


# ============================================================
# CONSTRUCTION STAGE
# ============================================================

@dataclass
class ConstructionStage:

    stage_number: int
    stage_name: str
    materials: List[CalculatedMaterial]


# ============================================================
# MASONRY CONSTANTS
# ============================================================

BRICK_LENGTH_M = 0.230
BRICK_HEIGHT_M = 0.076
BRICK_THICKNESS_M = 0.110

MORTAR_JOINT_M = 0.010

BRICK_WASTAGE = 0.05


# ============================================================
# CONCRETE CONSTANTS
# ============================================================

CONCRETE_CEMENT_PART = 1
CONCRETE_SAND_PART = 2
CONCRETE_STONE_PART = 4

CONCRETE_TOTAL_PARTS = 7

CONCRETE_DRY_VOLUME_FACTOR = 1.54


# ============================================================
# CEMENT
# ============================================================

CEMENT_DENSITY_KG_M3 = 1400.0
CEMENT_BAG_MASS_KG = 50.0

MATERIAL_WASTAGE = 0.05


# ============================================================
# MORTAR
# ============================================================

MORTAR_CEMENT_PART = 1
MORTAR_SAND_PART = 6

MORTAR_TOTAL_PARTS = 7

MORTAR_DRY_VOLUME_FACTOR = 1.33


# ============================================================
# HELPERS
# ============================================================

def calculate_cement_bags(
    cement_volume_m3: float,
) -> int:

    if cement_volume_m3 <= 0:
        return 0

    cement_mass_kg = (
        cement_volume_m3 *
        CEMENT_DENSITY_KG_M3
    )

    cement_mass_kg *= (
        1.0 + MATERIAL_WASTAGE
    )

    return ceil(
        cement_mass_kg /
        CEMENT_BAG_MASS_KG
    )


def calculate_concrete_materials(
    concrete_volume_m3: float,
) -> dict:

    if concrete_volume_m3 <= 0:

        return {
            "cement_bags": 0,
            "sand_m3": 0.0,
            "quarry_stone_m3": 0.0,
        }

    dry_volume = (
        concrete_volume_m3 *
        CONCRETE_DRY_VOLUME_FACTOR
    )

    cement_volume = (
        dry_volume *
        CONCRETE_CEMENT_PART /
        CONCRETE_TOTAL_PARTS
    )

    sand_volume = (
        dry_volume *
        CONCRETE_SAND_PART /
        CONCRETE_TOTAL_PARTS
    )

    stone_volume = (
        dry_volume *
        CONCRETE_STONE_PART /
        CONCRETE_TOTAL_PARTS
    )

    return {

        "cement_bags": calculate_cement_bags(
            cement_volume
        ),

        "sand_m3": round(
            sand_volume *
            (1.0 + MATERIAL_WASTAGE),
            3,
        ),

        "quarry_stone_m3": round(
            stone_volume *
            (1.0 + MATERIAL_WASTAGE),
            3,
        ),
    }


def calculate_mortar_materials(
    mortar_volume_m3: float,
) -> dict:

    if mortar_volume_m3 <= 0:

        return {
            "cement_bags": 0,
            "sand_m3": 0.0,
        }

    dry_volume = (
        mortar_volume_m3 *
        MORTAR_DRY_VOLUME_FACTOR
    )

    cement_volume = (
        dry_volume *
        MORTAR_CEMENT_PART /
        MORTAR_TOTAL_PARTS
    )

    sand_volume = (
        dry_volume *
        MORTAR_SAND_PART /
        MORTAR_TOTAL_PARTS
    )

    return {

        "cement_bags": calculate_cement_bags(
            cement_volume
        ),

        "sand_m3": round(
            sand_volume *
            (1.0 + MATERIAL_WASTAGE),
            3,
        ),
    }


def calculate_bricks(
    wall_area_m2: float,
) -> int:

    effective_length = (
        BRICK_LENGTH_M +
        MORTAR_JOINT_M
    )

    effective_height = (
        BRICK_HEIGHT_M +
        MORTAR_JOINT_M
    )

    brick_face_area = (
        effective_length *
        effective_height
    )

    base_quantity = (
        wall_area_m2 /
        brick_face_area
    )

    return ceil(
        base_quantity *
        (1.0 + BRICK_WASTAGE)
    )


# ============================================================
# STAGE 1 - FOUNDATION
# ============================================================

def calculate_foundation_stage(
    building,
) -> ConstructionStage:

    concrete = calculate_concrete_materials(
        building.foundation_volume_m3
    )

    water = (
        building.foundation_volume_m3 *
        180 *
        1.05
    )

    materials = [

        CalculatedMaterial(
            "Cement",
            concrete["cement_bags"],
            "bag",
            "Foundation concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Building sand",
            concrete["sand_m3"],
            "m3",
            "Foundation concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Quarry stone",
            concrete["quarry_stone_m3"],
            "m3",
            "Foundation concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Construction water",
            round(water, 2),
            "litres",
            "Foundation concrete × 180 L/m3 + 5%",
        ),
    ]

    return ConstructionStage(
        1,
        "Foundation",
        materials,
    )


# ============================================================
# STAGE 2 - WALLS
# ============================================================

def calculate_wall_stage(
    building,
) -> ConstructionStage:

    wall_area = (
        building.gross_wall_area_m2
    )

    brick_quantity = calculate_bricks(
        wall_area
    )

    WALL_CALCULATION_THICKNESS_M = 0.200

    masonry_volume = (
        building.total_wall_length_m *
        building.wall_height_m *
        WALL_CALCULATION_THICKNESS_M
    )

    brick_volume = (
        brick_quantity *
        BRICK_LENGTH_M *
        BRICK_HEIGHT_M *
        BRICK_THICKNESS_M
    )

    mortar_volume = max(
        0.0,
        masonry_volume -
        brick_volume,
    )

    mortar = calculate_mortar_materials(
        mortar_volume
    )

    dpc = (
        building.total_wall_length_m *
        1.05
    )

    opening_width = (
        building.total_door_opening_width_m +
        building.total_window_opening_width_m
    )

    lintel = opening_width * 1.10

    water = (
        mortar_volume *
        180 *
        1.05
    )

    materials = [

        CalculatedMaterial(
            "Standard brick",
            brick_quantity,
            "brick",
            "Gross wall area + 5% wastage",
        ),

        CalculatedMaterial(
            "Wall masonry",
            round(masonry_volume, 3),
            "m3",
            "Wall length × height × 0.200 m",
        ),

        CalculatedMaterial(
            "Wall mortar",
            round(mortar_volume, 3),
            "m3",
            "Masonry volume − brick volume",
        ),

        CalculatedMaterial(
            "Cement for wall mortar",
            mortar["cement_bags"],
            "bag",
            "Wall mortar × 1:6 mortar mix",
        ),

        CalculatedMaterial(
            "Building sand for wall mortar",
            mortar["sand_m3"],
            "m3",
            "Wall mortar × 1:6 mortar mix",
        ),

        CalculatedMaterial(
            "DPC",
            round(dpc, 3),
            "m",
            "Total wall length + 5%",
        ),

        CalculatedMaterial(
            "Lintel",
            round(lintel, 3),
            "m",
            "Door + window opening widths + 10%",
        ),

        CalculatedMaterial(
            "Construction water",
            round(water, 2),
            "litres",
            "Wall mortar × 180 L/m3 + 5%",
        ),
    ]

    return ConstructionStage(
        2,
        "Walls",
        materials,
    )


# ============================================================
# STAGE 3 - FLOOR / SLAB
# ============================================================

def calculate_floor_stage(
    building,
) -> ConstructionStage:

    hardcore = (
        building.hardcore_volume_m3 *
        1.05
    )

    dpm = (
        building.floor_area_m2 *
        1.10
    )

    slab = calculate_concrete_materials(
        building.slab_concrete_volume_m3
    )

    slab_water = (
        building.slab_concrete_volume_m3 *
        180 *
        1.05
    )

    materials = [

        CalculatedMaterial(
            "Hardcore",
            round(hardcore, 3),
            "m3",
            "Floor area × hardcore depth + 5%",
        ),

        CalculatedMaterial(
            "DPM",
            round(dpm, 3),
            "m2",
            "Floor area + 10%",
        ),

        CalculatedMaterial(
            "Slab concrete",
            round(
                building.slab_concrete_volume_m3,
                3,
            ),
            "m3",
            "Floor area × slab thickness",
        ),

        CalculatedMaterial(
            "Cement for slab",
            slab["cement_bags"],
            "bag",
            "Slab concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Building sand for slab",
            slab["sand_m3"],
            "m3",
            "Slab concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Quarry stone for slab",
            slab["quarry_stone_m3"],
            "m3",
            "Slab concrete × 1:2:4 mix",
        ),

        CalculatedMaterial(
            "Construction water",
            round(slab_water, 2),
            "litres",
            "Slab concrete × 180 L/m3 + 5%",
        ),
    ]

    return ConstructionStage(
        3,
        "Floor / Slab",
        materials,
    )


# ============================================================
# STAGE 4 - REINFORCEMENT & MASONRY REINFORCEMENT
# ============================================================

def calculate_reinforcement_stage(
    building,
    parameters,
) -> ConstructionStage:

    materials = []

    # ========================================================
    # 4.1 REINFORCEMENT STEEL
    # ========================================================

    reinforcement_length = (
        building.external_wall_length_m *
        parameters.reinforcement_runs
    )

    materials.append(
        CalculatedMaterial(
            "Reinforcement steel",
            round(
                reinforcement_length,
                3,
            ),
            "m",
            (
                "External wall length × "
                "reinforcement runs"
            ),
        )
    )

    # ========================================================
    # 4.2 BRICK FORCE
    # ========================================================

    # One brick course consists of:
    #
    # brick height + mortar joint
    #
    # 0.076 + 0.010 = 0.086 m

    effective_course_height = (
        BRICK_HEIGHT_M +
        MORTAR_JOINT_M
    )

    number_of_courses = ceil(
        building.wall_height_m /
        effective_course_height
    )

    brick_force_courses = ceil(
        number_of_courses /
        parameters.brick_force_interval_courses
    )

    # --------------------------------------------------------
    # External walls
    # --------------------------------------------------------

    external_brick_force_length = 0.0

    if parameters.brick_force_external_walls:

        external_brick_force_length = (
            building.external_wall_length_m *
            brick_force_courses
        )

    # --------------------------------------------------------
    # Internal walls
    # --------------------------------------------------------

    internal_brick_force_length = 0.0

    if parameters.brick_force_internal_walls:

        internal_brick_force_length = (
            building.internal_wall_length_m *
            brick_force_courses
        )

    total_brick_force_length = (
        external_brick_force_length +
        internal_brick_force_length
    )

    materials.append(
        CalculatedMaterial(
            "Brick force",
            round(
                total_brick_force_length,
                3,
            ),
            "m",
            (
                f"Brick force every "
                f"{parameters.brick_force_interval_courses} "
                f"courses × applicable wall lengths"
            ),
        )
    )

    # ========================================================
    # 4.3 REINFORCEMENT MESH
    # ========================================================

    if parameters.reinforcement_mesh_required:

        allowance = (
            1.0 +
            (
                parameters.mesh_allowance_percentage /
                100.0
            )
        )

        mesh_quantity = (
            building.floor_area_m2 *
            allowance
        )

        materials.append(
            CalculatedMaterial(
                "Reinforcement mesh",
                round(
                    mesh_quantity,
                    3,
                ),
                "m2",
                (
                    "Floor area + "
                    f"{parameters.mesh_allowance_percentage}% "
                    "allowance"
                ),
            )
        )

    # ========================================================
    # 4.4 BINDING WIRE
    # ========================================================

    # We do not calculate binding wire yet because the
    # quantity depends on the reinforcement specification
    # and tying arrangement.

    # ========================================================
    # REPORT INFORMATION
    # ========================================================

    print()
    print(
        "STAGE 4 CALCULATION DETAILS"
    )
    print("-" * 70)

    print(
        f"Wall courses:             "
        f"{number_of_courses}"
    )

    print(
        f"Brick-force courses:      "
        f"{brick_force_courses}"
    )

    print(
        f"External brick force:     "
        f"{external_brick_force_length:.3f} m"
    )

    print(
        f"Internal brick force:     "
        f"{internal_brick_force_length:.3f} m"
    )

    print(
        f"Total brick force:        "
        f"{total_brick_force_length:.3f} m"
    )

    return ConstructionStage(
        4,
        "Reinforcement & Masonry Reinforcement",
        materials,
    )


# ============================================================
# STAGE 5 - ROOFING
# ============================================================

def calculate_roofing_stage(
    building,
) -> ConstructionStage:

    return ConstructionStage(
        5,
        "Roofing - Excluded",
        [],
    )


# ============================================================
# COMPLETE CALCULATION
# ============================================================

def calculate_all_stages(
    building,
    parameters,
):

    return [

        calculate_foundation_stage(
            building
        ),

        calculate_wall_stage(
            building
        ),

        calculate_floor_stage(
            building
        ),

        calculate_reinforcement_stage(
            building,
            parameters,
        ),

        calculate_roofing_stage(
            building
        ),
    ]


# ============================================================
# REPORT
# ============================================================

def print_stage_report(
    building,
    stages,
):

    print()
    print("=" * 100)
    print(
        "ZIMBUILD AI - STAGE-BY-STAGE MATERIAL QUANTITIES"
    )
    print("=" * 100)

    print()
    print("BUILDING QUANTITIES")
    print("-" * 100)

    print(
        f"Floor area:              "
        f"{building.floor_area_m2:.3f} m²"
    )

    print(
        f"Wall count:              "
        f"{building.wall_count}"
    )

    print(
        f"Total wall length:       "
        f"{building.total_wall_length_m:.3f} m"
    )

    print(
        f"External wall length:    "
        f"{building.external_wall_length_m:.3f} m"
    )

    print(
        f"Internal wall length:    "
        f"{building.internal_wall_length_m:.3f} m"
    )

    print(
        f"Wall height:             "
        f"{building.wall_height_m:.3f} m"
    )

    print(
        f"Gross wall area:         "
        f"{building.gross_wall_area_m2:.3f} m²"
    )

    print(
        f"Foundation volume:       "
        f"{building.foundation_volume_m3:.3f} m³"
    )

    print(
        f"Slab concrete volume:    "
        f"{building.slab_concrete_volume_m3:.3f} m³"
    )

    print(
        f"Hardcore volume:         "
        f"{building.hardcore_volume_m3:.3f} m³"
    )

    total_lines = 0

    for stage in stages:

        print()
        print("=" * 100)

        print(
            f"STAGE {stage.stage_number} - "
            f"{stage.stage_name.upper()}"
        )

        print("=" * 100)

        if not stage.materials:

            if stage.stage_number == 5:

                print(
                    "Roofing is intentionally excluded."
                )

            continue

        print()

        print(
            f"{'MATERIAL':<42}"
            f"{'QUANTITY':>15}"
            f"{'UNIT':>12}"
        )

        print("-" * 100)

        for material in stage.materials:

            print(
                f"{material.material_name:<42}"
                f"{material.quantity:>15.3f}"
                f"{material.unit:>12}"
            )

            total_lines += 1

        print()

        print("Calculation basis:")

        for material in stage.materials:

            print(
                f"  - {material.material_name}: "
                f"{material.basis}"
            )

    print()
    print("=" * 100)

    print(
        f"Material quantity lines calculated: "
        f"{total_lines}"
    )

    print(
        "Roofing: EXCLUDED"
    )

    print("=" * 100)


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load Vision-derived plan data
    # --------------------------------------------------------

    parameters = (
        build_construction_parameters()
    )

    # --------------------------------------------------------
    # Ask user for construction parameters
    # --------------------------------------------------------

    parameters = (
        ask_for_missing_parameters(
            parameters
        )
    )

    # --------------------------------------------------------
    # Calculate building geometry quantities
    # --------------------------------------------------------

    building = (
        calculate_building_quantities(
            parameters
        )
    )

    # --------------------------------------------------------
    # Calculate material quantities
    # --------------------------------------------------------

    stages = (
        calculate_all_stages(
            building,
            parameters,
        )
    )

    # --------------------------------------------------------
    # Print report
    # --------------------------------------------------------

    print_stage_report(
        building,
        stages,
    )


if __name__ == "__main__":
    main()