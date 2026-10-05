"""
Vision Plan Analysis -> Material Estimation Adapter.

Converts the actual Vision Plan Analysis JSON structure
into the existing ZimBuild AI material-calculation models.

This module does not modify the existing Vision analyser,
Phase 9 quantity calculator, or material calculator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from estimation.models import BuildingQuantitySummary
from materials.models import MasonryParameters
from materials.material_calculator import calculate_building_materials


# ============================================================================
# DEFAULT CONSTRUCTION PARAMETERS
# ============================================================================

DEFAULT_WALL_HEIGHT_M = 2.7
DEFAULT_WALL_THICKNESS_M = 0.2
DEFAULT_WASTAGE_PERCENTAGE = 5.0


# ============================================================================
# JSON LOADING
# ============================================================================

def load_vision_analysis(
    json_path: Path,
) -> Dict[str, Any]:
    """Load the Vision Plan Analysis JSON."""

    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(
            f"Vision analysis file not found: {json_path}"
        )

    if not json_path.is_file():
        raise ValueError(
            f"Vision analysis path is not a file: {json_path}"
        )

    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Vision analysis JSON must contain a dictionary."
        )

    return data


# ============================================================================
# WALL EXTRACTION
# ============================================================================

def extract_vision_walls(
    analysis_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract external and internal walls from the actual
    Vision JSON structure.
    """

    walls_section = analysis_result.get("walls")

    if not isinstance(walls_section, dict):
        raise ValueError(
            "Vision analysis does not contain a valid 'walls' section."
        )

    external_walls = walls_section.get(
        "external_walls",
        [],
    )

    internal_walls = walls_section.get(
        "internal_walls",
        [],
    )

    if not isinstance(external_walls, list):
        external_walls = []

    if not isinstance(internal_walls, list):
        internal_walls = []

    walls: List[Dict[str, Any]] = []

    for wall in external_walls + internal_walls:

        if not isinstance(wall, dict):
            continue

        wall_id = wall.get("id")
        length_m = wall.get("length_m")
        thickness_m = wall.get("thickness_m")

        if wall_id is None:
            continue

        if length_m is None:
            continue

        try:
            length_m = float(length_m)
        except (TypeError, ValueError):
            continue

        if length_m <= 0:
            continue

        if thickness_m is not None:
            try:
                thickness_m = float(thickness_m)
            except (TypeError, ValueError):
                thickness_m = None

        walls.append(
            {
                "id": str(wall_id),
                "type": str(
                    wall.get(
                        "type",
                        "unknown",
                    )
                ).lower(),
                "length_m": length_m,
                "thickness_m": thickness_m,
                "confidence": wall.get("confidence"),
                "measurement_source": wall.get(
                    "measurement_source"
                ),
            }
        )

    if not walls:
        raise ValueError(
            "No valid walls were found in the Vision analysis."
        )

    return walls


# ============================================================================
# OPENING INFORMATION
# ============================================================================

def extract_opening_counts(
    analysis_result: Dict[str, Any],
) -> Tuple[int, int]:
    """
    Extract door and window counts.

    Opening areas are not calculated because the current
    Vision output has missing opening heights.
    """

    doors = analysis_result.get(
        "doors",
        {},
    )

    windows = analysis_result.get(
        "windows",
        {},
    )

    door_count = 0
    window_count = 0

    if isinstance(doors, dict):
        door_count = int(
            doors.get(
                "count",
                len(
                    doors.get(
                        "items",
                        [],
                    )
                ),
            )
        )

    if isinstance(windows, dict):
        window_count = int(
            windows.get(
                "count",
                len(
                    windows.get(
                        "items",
                        [],
                    )
                ),
            )
        )

    return door_count, window_count


# ============================================================================
# WALL QUANTITY CALCULATION + DIAGNOSTIC
# ============================================================================

def calculate_wall_quantities_from_vision(
    walls: List[Dict[str, Any]],
    wall_height_m: float,
    reported_total_length_m: float | None = None,
) -> Dict[str, float]:
    """
    Calculate wall quantities from the individual Vision
    wall measurements.

    Also prints a diagnostic breakdown comparing the
    extracted wall totals against the Vision summary.
    """

    if wall_height_m <= 0:
        raise ValueError(
            "wall_height_m must be greater than zero."
        )

    total_length = 0.0
    total_gross_area = 0.0
    total_volume = 0.0

    external_length = 0.0
    internal_length = 0.0

    external_count = 0
    internal_count = 0
    unknown_count = 0

    for wall in walls:

        length_m = wall["length_m"]
        thickness_m = wall["thickness_m"]

        if thickness_m is None:
            thickness_m = DEFAULT_WALL_THICKNESS_M

        wall_type = wall["type"]

        total_length += length_m

        total_gross_area += (
            length_m * wall_height_m
        )

        total_volume += (
            length_m
            * wall_height_m
            * thickness_m
        )

        if wall_type == "external":
            external_length += length_m
            external_count += 1

        elif wall_type == "internal":
            internal_length += length_m
            internal_count += 1

        else:
            unknown_count += 1

    # ------------------------------------------------------------------------
    # DIAGNOSTIC OUTPUT
    # ------------------------------------------------------------------------

    print()
    print("=" * 70)
    print("VISION WALL DIAGNOSTIC")
    print("=" * 70)

    print(
        f"External wall count:       {external_count}"
    )

    print(
        f"External wall length:      "
        f"{external_length:.3f} m"
    )

    print()

    print(
        f"Internal wall count:       {internal_count}"
    )

    print(
        f"Internal wall length:      "
        f"{internal_length:.3f} m"
    )

    print()

    print(
        f"Unknown wall count:        {unknown_count}"
    )

    print()

    print(
        f"Adapter total:             "
        f"{total_length:.3f} m"
    )

    if reported_total_length_m is not None:

        difference = (
            total_length
            - reported_total_length_m
        )

        print(
            f"Vision reported total:     "
            f"{reported_total_length_m:.3f} m"
        )

        print(
            f"Difference:                "
            f"{difference:.3f} m"
        )

    print("=" * 70)
    print()

    return {
        "total_wall_length_m": total_length,
        "total_gross_wall_area_m2": total_gross_area,
        "total_wall_volume_m3": total_volume,
    }


# ============================================================================
# BUILDING QUANTITY SUMMARY
# ============================================================================

def build_quantity_summary(
    analysis_result: Dict[str, Any],
    wall_height_m: float = DEFAULT_WALL_HEIGHT_M,
) -> BuildingQuantitySummary:
    """
    Convert Vision analysis into BuildingQuantitySummary.
    """

    walls = extract_vision_walls(
        analysis_result
    )

    # ------------------------------------------------------------------------
    # Get Vision's own reported total wall length.
    # ------------------------------------------------------------------------

    walls_section = analysis_result.get(
        "walls",
        {},
    )

    reported_total_length_m = None

    if isinstance(walls_section, dict):

        reported_total_length_m = (
            walls_section.get(
                "total_wall_length_m"
            )
        )

        if reported_total_length_m is not None:

            try:
                reported_total_length_m = float(
                    reported_total_length_m
                )
            except (TypeError, ValueError):
                reported_total_length_m = None

    # ------------------------------------------------------------------------
    # Calculate wall quantities.
    # ------------------------------------------------------------------------

    wall_quantities = (
        calculate_wall_quantities_from_vision(
            walls=walls,
            wall_height_m=wall_height_m,
            reported_total_length_m=(
                reported_total_length_m
            ),
        )
    )

    # ------------------------------------------------------------------------
    # Door/window counts.
    # ------------------------------------------------------------------------

    door_count, window_count = (
        extract_opening_counts(
            analysis_result
        )
    )

    # ------------------------------------------------------------------------
    # Opening areas.
    #
    # The current Vision output contains widths but missing
    # heights for the detected doors/windows. Therefore we
    # do not fabricate opening areas.
    # ------------------------------------------------------------------------

    total_opening_area_m2 = 0.0

    total_net_wall_area_m2 = (
        wall_quantities[
            "total_gross_wall_area_m2"
        ]
        - total_opening_area_m2
    )

    # ------------------------------------------------------------------------
    # Room information.
    # ------------------------------------------------------------------------

    rooms = analysis_result.get(
        "rooms",
        {},
    )

    if isinstance(rooms, dict):
        room_count = int(
            rooms.get(
                "count",
                0,
            )
        )
    else:
        room_count = 0

    # ------------------------------------------------------------------------
    # Floor information.
    #
    # Vision recommends the printed floor area.
    # ------------------------------------------------------------------------

    floor = analysis_result.get(
        "floor",
        {},
    )

    if isinstance(floor, dict):

        floor_area = floor.get(
            "recommended_floor_area_m2"
        )

        if floor_area is None:
            floor_area = floor.get(
                "printed_total_floor_area_m2",
                0.0,
            )

    else:
        floor_area = 0.0

    if floor_area is None:
        floor_area = 0.0

    try:
        floor_area = float(floor_area)
    except (TypeError, ValueError):
        floor_area = 0.0

    # ------------------------------------------------------------------------
    # Roof information.
    # ------------------------------------------------------------------------

    roof = analysis_result.get(
        "roof",
        {},
    )

    if isinstance(roof, dict):

        roof_present = bool(
            roof.get(
                "present",
                False,
            )
        )

        roof_area = roof.get(
            "area_m2"
        )

    else:

        roof_present = False
        roof_area = None

    # ------------------------------------------------------------------------
    # Return standard ZimBuild AI quantity model.
    # ------------------------------------------------------------------------

    return BuildingQuantitySummary(

        wall_count=len(walls),

        total_wall_length_m=(
            wall_quantities[
                "total_wall_length_m"
            ]
        ),

        total_gross_wall_area_m2=(
            wall_quantities[
                "total_gross_wall_area_m2"
            ]
        ),

        total_opening_area_m2=(
            total_opening_area_m2
        ),

        total_net_wall_area_m2=(
            total_net_wall_area_m2
        ),

        total_wall_volume_m3=(
            wall_quantities[
                "total_wall_volume_m3"
            ]
        ),

        door_count=door_count,

        window_count=window_count,

        total_door_area_m2=0.0,

        total_window_area_m2=0.0,

        room_count=room_count,

        total_floor_area_m2=floor_area,

        roof_present=roof_present,

        roof_area_m2=roof_area,
    )


# ============================================================================
# MASONRY PARAMETERS
# ============================================================================

def build_masonry_parameters(
    wall_thickness_m: float = DEFAULT_WALL_THICKNESS_M,
    wastage_percentage: float = DEFAULT_WASTAGE_PERCENTAGE,
) -> MasonryParameters:
    """
    Build MasonryParameters for the existing material calculator.
    """

    if wall_thickness_m <= 0:
        raise ValueError(
            "wall_thickness_m must be greater than zero."
        )

    if wastage_percentage < 0:
        raise ValueError(
            "wastage_percentage cannot be negative."
        )

    return MasonryParameters(
        wall_thickness_m=wall_thickness_m,
        wastage_percentage=wastage_percentage,
    )


# ============================================================================
# COMPLETE VISION -> MATERIAL FLOW
# ============================================================================

def calculate_materials_from_vision(
    json_path: Path,
    wall_height_m: float = DEFAULT_WALL_HEIGHT_M,
    wall_thickness_m: float = DEFAULT_WALL_THICKNESS_M,
    wastage_percentage: float = DEFAULT_WASTAGE_PERCENTAGE,
):
    """
    Complete Vision -> quantities -> materials flow.
    """

    analysis_result = load_vision_analysis(
        json_path
    )

    quantity_summary = build_quantity_summary(
        analysis_result=analysis_result,
        wall_height_m=wall_height_m,
    )

    masonry_parameters = (
        build_masonry_parameters(
            wall_thickness_m=wall_thickness_m,
            wastage_percentage=wastage_percentage,
        )
    )

    material_summary = (
        calculate_building_materials(
            quantity_summary=quantity_summary,
            masonry_parameters=masonry_parameters,
        )
    )

    return (
        quantity_summary,
        masonry_parameters,
        material_summary,
    )


# ============================================================================
# DIAGNOSTIC RUNNER
# ============================================================================

def run_vision_material_adapter(
    json_path: Path,
) -> Dict[str, Any]:
    """
    Run the adapter and return a diagnostic result.
    """

    (
        quantity_summary,
        masonry_parameters,
        material_summary,
    ) = calculate_materials_from_vision(
        json_path=json_path,
    )

    return {
        "status": "success",

        "quantity_summary": {

            "wall_count": (
                quantity_summary.wall_count
            ),

            "total_wall_length_m": (
                quantity_summary.total_wall_length_m
            ),

            "total_gross_wall_area_m2": (
                quantity_summary.total_gross_wall_area_m2
            ),

            "total_opening_area_m2": (
                quantity_summary.total_opening_area_m2
            ),

            "total_net_wall_area_m2": (
                quantity_summary.total_net_wall_area_m2
            ),

            "total_wall_volume_m3": (
                quantity_summary.total_wall_volume_m3
            ),

            "door_count": (
                quantity_summary.door_count
            ),

            "window_count": (
                quantity_summary.window_count
            ),

            "room_count": (
                quantity_summary.room_count
            ),

            "total_floor_area_m2": (
                quantity_summary.total_floor_area_m2
            ),

            "roof_present": (
                quantity_summary.roof_present
            ),

            "roof_area_m2": (
                quantity_summary.roof_area_m2
            ),
        },

        "masonry_parameters": {

            "wall_thickness_m": (
                masonry_parameters.wall_thickness_m
            ),

            "wastage_percentage": (
                masonry_parameters.wastage_percentage
            ),
        },

        "material_summary": material_summary,
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":

    vision_json = Path(
        "ml/results/vision_plan_analysis.json"
    )

    result = run_vision_material_adapter(
        vision_json
    )

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )