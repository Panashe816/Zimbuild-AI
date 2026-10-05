"""
ZimBuild AI - Construction Parameters Service

This service:

1. Reads geometry detected by the Vision system.
2. Identifies construction information that cannot reliably
   be obtained from the architectural plan.
3. Allows the user to enter those construction parameters.
4. Collects Stage 4 reinforcement and masonry specifications.

These interactive inputs are a prototype of the same form
that will later be implemented in the ZimBuild AI frontend.

Roofing is intentionally not handled here.
"""

import json

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_VISION_FILE = (
    PROJECT_ROOT
    / "ml"
    / "results"
    / "vision_plan_analysis.json"
)


# ============================================================
# CONSTRUCTION PARAMETERS
# ============================================================

@dataclass
class ConstructionParameters:

    # --------------------------------------------------------
    # PLAN-DERIVED GEOMETRY
    # --------------------------------------------------------

    floor_area_m2: Optional[float] = None

    wall_count: int = 0

    total_wall_length_m: float = 0.0

    external_wall_length_m: float = 0.0

    internal_wall_length_m: float = 0.0

    wall_thicknesses_m: List[float] = field(
        default_factory=list
    )

    room_count: int = 0

    door_count: int = 0

    window_count: int = 0

    total_door_opening_width_m: float = 0.0

    total_window_opening_width_m: float = 0.0

    scale: Optional[str] = None

    # --------------------------------------------------------
    # BASIC CONSTRUCTION PARAMETERS
    # --------------------------------------------------------

    wall_height_m: Optional[float] = None

    foundation_width_m: Optional[float] = None

    foundation_depth_m: Optional[float] = None

    slab_thickness_m: Optional[float] = None

    hardcore_depth_m: Optional[float] = None

    # --------------------------------------------------------
    # STAGE 4 - REINFORCEMENT & MASONRY
    # --------------------------------------------------------

    reinforcement_runs: Optional[int] = None

    brick_force_interval_courses: Optional[int] = None

    brick_force_external_walls: Optional[bool] = None

    brick_force_internal_walls: Optional[bool] = None

    reinforcement_mesh_required: Optional[bool] = None

    mesh_allowance_percentage: Optional[float] = None

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    required_inputs: List[str] = field(
        default_factory=list
    )

    sources: Dict[str, str] = field(
        default_factory=dict
    )


# ============================================================
# SAFE CONVERSION HELPERS
# ============================================================

def _safe_float(
    value,
    default=None,
):

    if value is None:
        return default

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _safe_int(
    value,
    default=0,
):

    if value is None:
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# PLAN DATA EXTRACTION
# ============================================================

def extract_plan_data(
    vision_data: dict,
) -> ConstructionParameters:
    """
    Extract measurable building information from the Vision
    analysis JSON.

    Only information actually present in the Vision result is
    extracted here.

    Construction specifications that are not present in the
    plan are collected later through user input.
    """

    drawing = vision_data.get(
        "drawing",
        {}
    )

    scale_data = vision_data.get(
        "scale",
        {}
    )

    walls = vision_data.get(
        "walls",
        {}
    )

    rooms = vision_data.get(
        "rooms",
        {}
    )

    doors = vision_data.get(
        "doors",
        {}
    )

    windows = vision_data.get(
        "windows",
        {}
    )

    floor = vision_data.get(
        "floor",
        {}
    )

    # ========================================================
    # FLOOR AREA
    # ========================================================

    floor_area = (
        floor.get(
            "recommended_floor_area_m2"
        )
    )

    if floor_area is None:

        floor_area = (
            floor.get(
                "printed_total_floor_area_m2"
            )
        )

    if floor_area is None:

        floor_area = (
            drawing.get(
                "printed_total_floor_area_m2"
            )
        )

    floor_area = _safe_float(
        floor_area
    )

    # ========================================================
    # WALLS
    # ========================================================

    external_walls = walls.get(
        "external_walls",
        []
    )

    internal_walls = walls.get(
        "internal_walls",
        []
    )

    all_walls = (
        external_walls +
        internal_walls
    )

    wall_count = _safe_int(
        walls.get(
            "count"
        ),
        len(all_walls),
    )

    external_wall_length = sum(
        _safe_float(
            wall.get("length_m"),
            0.0,
        )
        for wall in external_walls
    )

    internal_wall_length = sum(
        _safe_float(
            wall.get("length_m"),
            0.0,
        )
        for wall in internal_walls
    )

    total_wall_length = (
        external_wall_length
        +
        internal_wall_length
    )

    # --------------------------------------------------------
    # Wall thicknesses
    # --------------------------------------------------------

    wall_thicknesses = sorted(
        {
            round(
                _safe_float(
                    wall.get("thickness_m"),
                    0.0,
                ),
                3,
            )
            for wall in all_walls
            if wall.get("thickness_m") is not None
        }
    )

    # ========================================================
    # ROOMS
    # ========================================================

    room_items = rooms.get(
        "items",
        []
    )

    room_count = _safe_int(
        rooms.get(
            "count"
        ),
        len(room_items),
    )

    # ========================================================
    # DOORS
    # ========================================================

    door_items = doors.get(
        "items",
        []
    )

    door_count = _safe_int(
        doors.get(
            "count"
        ),
        len(door_items),
    )

    total_door_opening_width = sum(
        _safe_float(
            door.get("width_m"),
            0.0,
        )
        for door in door_items
    )

    # ========================================================
    # WINDOWS
    # ========================================================

    window_items = windows.get(
        "items",
        []
    )

    window_count = _safe_int(
        windows.get(
            "count"
        ),
        len(window_items),
    )

    total_window_opening_width = sum(
        _safe_float(
            window.get("width_m"),
            0.0,
        )
        for window in window_items
    )

    # ========================================================
    # SCALE
    # ========================================================

    scale = (
        scale_data.get(
            "user_selected"
        )
        or
        scale_data.get(
            "detected_scale"
        )
        or
        drawing.get(
            "scale"
        )
    )

    # ========================================================
    # BUILD RESULT
    # ========================================================

    return ConstructionParameters(

        floor_area_m2=floor_area,

        wall_count=wall_count,

        total_wall_length_m=round(
            total_wall_length,
            3,
        ),

        external_wall_length_m=round(
            external_wall_length,
            3,
        ),

        internal_wall_length_m=round(
            internal_wall_length,
            3,
        ),

        wall_thicknesses_m=wall_thicknesses,

        room_count=room_count,

        door_count=door_count,

        window_count=window_count,

        total_door_opening_width_m=round(
            total_door_opening_width,
            3,
        ),

        total_window_opening_width_m=round(
            total_window_opening_width,
            3,
        ),

        scale=scale,

        sources={
            "floor_area": "Vision analysis",
            "walls": "Vision analysis",
            "rooms": "Vision analysis",
            "doors": "Vision analysis",
            "windows": "Vision analysis",
            "scale": "Vision analysis",
        },
    )


# ============================================================
# LOAD VISION ANALYSIS
# ============================================================

def build_construction_parameters(
    vision_file: Path = DEFAULT_VISION_FILE,
) -> ConstructionParameters:
    """
    Load the Vision analysis JSON and extract plan geometry.
    """

    if not vision_file.exists():

        raise FileNotFoundError(
            "\nVision analysis file not found:\n"
            f"{vision_file}\n"
        )

    with open(
        vision_file,
        "r",
        encoding="utf-8",
    ) as file:

        vision_data = json.load(file)

    return extract_plan_data(
        vision_data
    )


# ============================================================
# USER INPUT HELPERS
# ============================================================

def ask_positive_float(
    prompt: str,
) -> float:
    """
    Ask for a positive decimal value.
    """

    while True:

        try:

            value = float(
                input(prompt).strip()
            )

            if value <= 0:

                print(
                    "Please enter a value greater than 0."
                )

                continue

            return value

        except ValueError:

            print(
                "Invalid value. "
                "Please enter a number, for example 2.7."
            )


def ask_positive_integer(
    prompt: str,
) -> int:
    """
    Ask for a positive whole number.
    """

    while True:

        try:

            value = int(
                input(prompt).strip()
            )

            if value <= 0:

                print(
                    "Please enter a whole number greater than 0."
                )

                continue

            return value

        except ValueError:

            print(
                "Invalid value. "
                "Please enter a whole number."
            )


def ask_yes_no(
    prompt: str,
    default: bool = True,
) -> bool:
    """
    Ask a Yes/No question.

    Pressing Enter accepts the default.
    """

    default_text = (
        "Y"
        if default
        else "N"
    )

    while True:

        answer = input(
            f"{prompt} [{default_text}] "
        ).strip().upper()

        # ----------------------------------------------------
        # Enter = default
        # ----------------------------------------------------

        if answer == "":

            return default

        # ----------------------------------------------------
        # Yes
        # ----------------------------------------------------

        if answer in (
            "Y",
            "YES",
        ):

            return True

        # ----------------------------------------------------
        # No
        # ----------------------------------------------------

        if answer in (
            "N",
            "NO",
        ):

            return False

        print(
            "Please enter Y or N."
        )


# ============================================================
# BASIC CONSTRUCTION INPUTS
# ============================================================

def ask_for_basic_parameters(
    parameters: ConstructionParameters,
) -> ConstructionParameters:
    """
    Ask for construction dimensions that cannot reliably
    be obtained from the architectural plan.
    """

    print()
    print("=" * 70)
    print(
        "CONSTRUCTION INFORMATION REQUIRED FROM USER"
    )
    print("=" * 70)

    print()

    print(
        "Some construction information could not be reliably "
        "detected from the architectural plan."
    )

    print(
        "Please enter the missing values below."
    )

    # ========================================================
    # WALL HEIGHT
    # ========================================================

    if parameters.wall_height_m is None:

        print()

        print(
            "Wall height was not detected from the plan."
        )

        parameters.wall_height_m = (
            ask_positive_float(
                "Enter wall height (m): "
            )
        )

    # ========================================================
    # FOUNDATION WIDTH
    # ========================================================

    if parameters.foundation_width_m is None:

        print()

        print(
            "Foundation width was not detected from the plan."
        )

        parameters.foundation_width_m = (
            ask_positive_float(
                "Enter foundation width (m): "
            )
        )

    # ========================================================
    # FOUNDATION DEPTH
    # ========================================================

    if parameters.foundation_depth_m is None:

        print()

        print(
            "Foundation depth was not detected from the plan."
        )

        parameters.foundation_depth_m = (
            ask_positive_float(
                "Enter foundation depth (m): "
            )
        )

    # ========================================================
    # SLAB THICKNESS
    # ========================================================

    if parameters.slab_thickness_m is None:

        print()

        print(
            "Slab thickness was not detected from the plan."
        )

        parameters.slab_thickness_m = (
            ask_positive_float(
                "Enter slab thickness (m): "
            )
        )

    # ========================================================
    # HARDCORE DEPTH
    # ========================================================

    if parameters.hardcore_depth_m is None:

        print()

        print(
            "Hardcore depth was not detected from the plan."
        )

        parameters.hardcore_depth_m = (
            ask_positive_float(
                "Enter hardcore depth (m): "
            )
        )

    return parameters


# ============================================================
# STAGE 4 INPUTS
# ============================================================

def ask_for_stage4_parameters(
    parameters: ConstructionParameters,
) -> ConstructionParameters:
    """
    Ask for reinforcement and masonry reinforcement rules.

    Default values:

        Reinforcement runs: 3
        Brick force interval: every 4 courses
        External brick force: Yes
        Internal brick force: Yes
        Reinforcement mesh: Yes
        Mesh allowance: 10%
    """

    print()
    print("=" * 70)
    print(
        "REINFORCEMENT & MASONRY SPECIFICATIONS"
    )
    print("=" * 70)

    print()

    print(
        "These values are construction rules used for "
        "quantity estimation."
    )

    print(
        "Press Enter to use the displayed default."
    )

    # ========================================================
    # REINFORCEMENT RUNS
    # ========================================================

    if parameters.reinforcement_runs is None:

        while True:

            answer = input(
                "Reinforcement runs around external walls: [3] "
            ).strip()

            if answer == "":

                parameters.reinforcement_runs = 3

                break

            try:

                value = int(answer)

                if value <= 0:

                    print(
                        "Please enter a whole number greater than 0."
                    )

                    continue

                parameters.reinforcement_runs = value

                break

            except ValueError:

                print(
                    "Invalid value. "
                    "Please enter a whole number."
                )

    # ========================================================
    # BRICK FORCE INTERVAL
    # ========================================================

    if parameters.brick_force_interval_courses is None:

        while True:

            answer = input(
                "Brick force interval (brick courses): [4] "
            ).strip()

            if answer == "":

                parameters.brick_force_interval_courses = 4

                break

            try:

                value = int(answer)

                if value <= 0:

                    print(
                        "Please enter a whole number greater than 0."
                    )

                    continue

                parameters.brick_force_interval_courses = value

                break

            except ValueError:

                print(
                    "Invalid value. "
                    "Please enter a whole number."
                )

    # ========================================================
    # EXTERNAL WALL BRICK FORCE
    # ========================================================

    if parameters.brick_force_external_walls is None:

        parameters.brick_force_external_walls = (
            ask_yes_no(
                "Apply brick force to external walls?",
                default=True,
            )
        )

    # ========================================================
    # INTERNAL WALL BRICK FORCE
    # ========================================================

    if parameters.brick_force_internal_walls is None:

        parameters.brick_force_internal_walls = (
            ask_yes_no(
                "Apply brick force to internal walls?",
                default=True,
            )
        )

    # ========================================================
    # REINFORCEMENT MESH
    # ========================================================

    if parameters.reinforcement_mesh_required is None:

        parameters.reinforcement_mesh_required = (
            ask_yes_no(
                "Reinforcement mesh required for slab?",
                default=True,
            )
        )

    # ========================================================
    # MESH ALLOWANCE
    # ========================================================

    if parameters.reinforcement_mesh_required:

        if parameters.mesh_allowance_percentage is None:

            while True:

                answer = input(
                    "Mesh allowance (%): [10] "
                ).strip()

                if answer == "":

                    parameters.mesh_allowance_percentage = 10.0

                    break

                try:

                    value = float(answer)

                    if value < 0:

                        print(
                            "Allowance cannot be negative."
                        )

                        continue

                    parameters.mesh_allowance_percentage = value

                    break

                except ValueError:

                    print(
                        "Invalid value. "
                        "Please enter a number, for example 10."
                    )

    else:

        parameters.mesh_allowance_percentage = 0.0

    return parameters


# ============================================================
# COMPLETE USER INPUT
# ============================================================

def ask_for_missing_parameters(
    parameters: ConstructionParameters,
) -> ConstructionParameters:
    """
    Collect all construction information required by the
    quantity calculation pipeline.
    """

    parameters = ask_for_basic_parameters(
        parameters
    )

    parameters = ask_for_stage4_parameters(
        parameters
    )

    parameters.required_inputs = []

    return parameters


# ============================================================
# REPORT
# ============================================================

def print_report(
    parameters: ConstructionParameters,
):

    print()
    print("=" * 70)
    print(
        "ZIMBUILD AI - CONSTRUCTION PARAMETERS"
    )
    print("=" * 70)

    # ========================================================
    # PLAN DATA
    # ========================================================

    print()
    print(
        "DETECTED FROM UPLOADED PLAN"
    )

    print("-" * 70)

    print(
        f"Floor area:              "
        f"{parameters.floor_area_m2} m²"
    )

    print(
        f"Wall count:              "
        f"{parameters.wall_count}"
    )

    print(
        f"Total wall length:       "
        f"{parameters.total_wall_length_m:.3f} m"
    )

    print(
        f"External wall length:    "
        f"{parameters.external_wall_length_m:.3f} m"
    )

    print(
        f"Internal wall length:    "
        f"{parameters.internal_wall_length_m:.3f} m"
    )

    print(
        f"Wall thicknesses:        "
        f"{parameters.wall_thicknesses_m}"
    )

    print(
        f"Rooms:                   "
        f"{parameters.room_count}"
    )

    print(
        f"Doors:                   "
        f"{parameters.door_count}"
    )

    print(
        f"Windows:                 "
        f"{parameters.window_count}"
    )

    print(
        f"Door opening width:      "
        f"{parameters.total_door_opening_width_m:.3f} m"
    )

    print(
        f"Window opening width:    "
        f"{parameters.total_window_opening_width_m:.3f} m"
    )

    print(
        f"Scale:                   "
        f"{parameters.scale}"
    )

    # ========================================================
    # BASIC CONSTRUCTION
    # ========================================================

    print()
    print(
        "CONSTRUCTION PARAMETERS"
    )

    print("-" * 70)

    print(
        f"Wall height:             "
        f"{parameters.wall_height_m} m"
    )

    print(
        f"Foundation width:        "
        f"{parameters.foundation_width_m} m"
    )

    print(
        f"Foundation depth:        "
        f"{parameters.foundation_depth_m} m"
    )

    print(
        f"Slab thickness:          "
        f"{parameters.slab_thickness_m} m"
    )

    print(
        f"Hardcore depth:          "
        f"{parameters.hardcore_depth_m} m"
    )

    # ========================================================
    # STAGE 4
    # ========================================================

    print()
    print(
        "REINFORCEMENT & MASONRY SPECIFICATIONS"
    )

    print("-" * 70)

    print(
        f"Reinforcement runs:      "
        f"{parameters.reinforcement_runs}"
    )

    print(
        f"Brick force interval:    "
        f"every {parameters.brick_force_interval_courses} "
        f"courses"
    )

    print(
        f"Brick force external:    "
        f"{parameters.brick_force_external_walls}"
    )

    print(
        f"Brick force internal:    "
        f"{parameters.brick_force_internal_walls}"
    )

    print(
        f"Reinforcement mesh:      "
        f"{parameters.reinforcement_mesh_required}"
    )

    print(
        f"Mesh allowance:          "
        f"{parameters.mesh_allowance_percentage}%"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    parameters = (
        build_construction_parameters()
    )

    parameters = (
        ask_for_missing_parameters(
            parameters
        )
    )

    print_report(
        parameters
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()