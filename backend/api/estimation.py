"""
ZimBuild AI - Construction Estimation API

API bridge for the NEW AI visualisation pipeline.

Flow:
    Uploaded/processed plan
        -> new vision_plan_analyser.py
        -> vision_plan_analysis.json
        -> ConstructionParameters
        -> BuildingQuantities
        -> Material quantities / four construction stages
        -> Stage pricing
        -> 12% labour
        -> 4% stage transport
        -> location adjustment
        -> frontend-friendly BoQ response

Construction stages:
    1. Foundation / Footing
    2. Slab
    3. Walls
    4. Reinforcement

Roofing is intentionally excluded.
"""

from dataclasses import asdict, is_dataclass
import importlib
import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import engine
from backend.models import Estimate, Plan, User

from backend.services.construction_parameters_service import extract_plan_data
from backend.services.building_quantity_service import calculate_building_quantities
from backend.services.plan_material_quantity_service import (
    calculate_all_stages,
    CalculatedMaterial,
)
from backend.services.pricing_integration_service import (
    price_all_stages,
    apply_labour_to_stage_results,
    calculate_overall_material_subtotal,
    calculate_stage_transport,
    calculate_location_adjusted_total,
    DISPLAY_STAGE_NAMES,
    DISPLAY_STAGE_ORDER,
    LOCATION_NAMES,
    LOCATION_FACTORS,
)


router = APIRouter(
    prefix="/estimation",
    tags=["Estimation"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VISION_RESULT_PATH = PROJECT_ROOT / "ml" / "results" / "vision_plan_analysis.json"
PROCESSED_PLANS_DIR = PROJECT_ROOT / "backend" / "processed_plans"


LOCATION_ALIASES = {
    "city": "city_town",
    "city_town": "city_town",
    "big_town": "city_town",
    "small_town": "growth_point",
    "growth_point": "growth_point",
    "rural": "rural_farm",
    "farm": "rural_farm",
    "rural_farm": "rural_farm",
}

# The active pricing service uses these numeric location factors for the
# final project adjustment, while its material pricing accepts the string
# profile IDs used by the frontend.
LOCATION_FACTOR_BY_PROFILE = {
    "city_town": 1.20,
    "growth_point": 1.00,
    "rural_farm": 0.80,
}

LOCATION_NAME_BY_PROFILE = {
    "city_town": "City / Big Town",
    "growth_point": "Small Town / Growth Point",
    "rural_farm": "Rural Area / Farm",
}


# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------


def _debug_log(message: str, started_at: float | None = None) -> None:
    if started_at is None:
        print(f"\n[ZIMBUILD DEBUG] {message}", flush=True)
        return

    elapsed = time.perf_counter() - started_at
    print(
        f"\n[ZIMBUILD DEBUG +{elapsed:8.2f}s] {message}",
        flush=True,
    )


def _serialize(value: Any) -> Any:
    """Convert dataclasses and nested values to JSON-safe structures."""

    if is_dataclass(value):
        return {
            key: _serialize(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]

    if isinstance(value, Path):
        return str(value)

    return value


def _json_safe(value: Any) -> Any:
    """Recursively normalise values for FastAPI/JSON responses."""

    value = _serialize(value)

    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None

    return value


def _assert_plan_owner(processed_filename: str, current_user: User) -> None:
    """Prevent a user from estimating a plan uploaded by another account."""
    with Session(engine) as db:
        plan = db.query(Plan).filter(Plan.stored_filename == processed_filename).one_or_none()
        if plan is None or plan.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Processed plan not found.")


def _get_processed_plan_path(processed_filename: str) -> Path:
    """Resolve a frontend-supplied processed filename safely."""

    filename = Path(processed_filename).name

    if filename != processed_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid processed filename.",
        )

    path = PROCESSED_PLANS_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Processed plan not found: {filename}",
        )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Processed plan path is not a file.",
        )

    return path


def _normalise_location_profile(location_profile_id: str) -> str:
    """Normalise frontend location values to the three supported profiles."""

    key = str(location_profile_id).strip().lower()

    if key in {"1", "city", "city_town", "big_town"}:
        return "city_town"

    if key in {"2", "small_town", "growth_point"}:
        return "growth_point"

    if key in {"3", "rural", "farm", "rural_farm"}:
        return "rural_farm"

    raise HTTPException(
        status_code=400,
        detail=(
            "Invalid project location category. Use city_town, "
            "growth_point or rural_farm."
        ),
    )


def _location_factor(location_profile_id: str) -> float:
    profile = _normalise_location_profile(location_profile_id)
    return LOCATION_FACTOR_BY_PROFILE[profile]


def _location_name(location_profile_id: str) -> str:
    profile = _normalise_location_profile(location_profile_id)
    return LOCATION_NAME_BY_PROFILE[profile]


# ----------------------------------------------------------------------
# NEW AI VISUALISATION PIPELINE
# ----------------------------------------------------------------------


def _run_new_ai_visualiser(
    image_path: Path,
    scale_ratio: float,
) -> Dict[str, Any]:
    """
    Run the project's NEW vision_plan_analyser.py.

    The analyser was originally written as a command-line script and keeps
    its image path and selected scale as module-level settings. This API
    adapts that existing script without rewriting it.
    """

    try:
        analyser = importlib.import_module(
            "ml.scripts.vision_plan_analyser"
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not load the new AI visualisation module "
            "ml.scripts.vision_plan_analyser."
            f" Details: {exc}"
        ) from exc

    analyser.IMAGE_PATH = Path(image_path)
    analyser.USER_SCALE_RATIO = float(scale_ratio)

    # The existing analyser writes the authoritative result to this file.
    analyser.analyse_plan()

    if not VISION_RESULT_PATH.exists():
        raise RuntimeError(
            "The AI visualiser completed without producing "
            f"{VISION_RESULT_PATH}."
        )

    try:
        with open(VISION_RESULT_PATH, "r", encoding="utf-8") as file:
            analysis = json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"The AI visualiser produced invalid JSON: {exc}"
        ) from exc

    if not isinstance(analysis, dict):
        raise RuntimeError("The AI visualiser result is not a JSON object.")

    return analysis


def _validate_vision_result(analysis: Dict[str, Any]) -> None:
    """
    Validate the actual JSON schema produced by the NEW Vision analyser.

    IMPORTANT:
    The Vision analyser does NOT return ``walls.items``. It returns two
    wall collections:

        walls.external_walls
        walls.internal_walls

    The construction_parameters_service already understands this schema, so
    the API must validate the same structure instead of inventing a different
    one.
    """

    if not isinstance(analysis, dict):
        raise ValueError("AI visualisation returned an invalid result object.")

    status = analysis.get("analysis_status")
    if status not in (None, "success"):
        raise ValueError(
            f"AI visualisation did not complete successfully. Status: {status}"
        )

    walls = analysis.get("walls")
    floor = analysis.get("floor")

    if not isinstance(walls, dict):
        raise ValueError(
            "AI visualisation did not return a valid walls object."
        )

    if not isinstance(floor, dict):
        raise ValueError(
            "AI visualisation did not return a valid floor object."
        )

    external_walls = walls.get("external_walls") or []
    internal_walls = walls.get("internal_walls") or []

    # The NEW Vision JSON stores usable wall segments in these two lists.
    # Keep a small backwards-compatible fallback for older result files that
    # may contain a generic ``items`` list.
    wall_items = []

    if isinstance(external_walls, list):
        wall_items.extend(external_walls)

    if isinstance(internal_walls, list):
        wall_items.extend(internal_walls)

    if not wall_items:
        legacy_items = walls.get("items")
        if isinstance(legacy_items, list):
            wall_items = legacy_items

    if not wall_items:
        raise ValueError(
            "AI visualisation did not detect any usable wall segments. "
            "The Vision result contains no external_walls or internal_walls."
        )

    # A wall is only useful to the quantity engine if at least one segment
    # contains a positive measured length.
    usable_wall_count = 0

    for wall in wall_items:
        if not isinstance(wall, dict):
            continue

        try:
            length_m = float(wall.get("length_m", 0) or 0)
        except (TypeError, ValueError):
            length_m = 0.0

        if length_m > 0:
            usable_wall_count += 1

    if usable_wall_count == 0:
        raise ValueError(
            "AI visualisation detected wall entries, but none has a valid "
            "positive length in metres."
        )

    # The Vision analyser deliberately prioritises the printed/recommended
    # floor area when available.
    floor_area = floor.get("recommended_floor_area_m2")

    if floor_area is None:
        floor_area = floor.get("printed_total_floor_area_m2")

    try:
        floor_area = float(floor_area)
    except (TypeError, ValueError):
        floor_area = 0.0

    if floor_area <= 0:
        raise ValueError(
            "AI visualisation did not provide a valid floor area."
        )


# ----------------------------------------------------------------------
# Construction parameters
# ----------------------------------------------------------------------


def _build_construction_parameters(
    analysis_result: Dict[str, Any],
    *,
    wall_height_m: float,
    wall_thickness_m: float,
    foundation_width_m: float,
    foundation_depth_m: float,
    slab_thickness_m: float,
    hardcore_depth_m: float,
    reinforcement_runs: int,
    brick_force_interval_courses: int,
    mesh_required: bool,
    mesh_allowance_percentage: float,
) -> Any:
    """Convert Vision geometry plus frontend inputs into ConstructionParameters."""

    parameters = extract_plan_data(analysis_result)

    parameters.wall_height_m = float(wall_height_m)
    parameters.foundation_width_m = float(foundation_width_m)
    parameters.foundation_depth_m = float(foundation_depth_m)
    parameters.slab_thickness_m = float(slab_thickness_m)
    parameters.hardcore_depth_m = float(hardcore_depth_m)
    parameters.reinforcement_runs = int(reinforcement_runs)
    parameters.brick_force_interval_courses = int(brick_force_interval_courses)
    parameters.brick_force_external_walls = True
    parameters.brick_force_internal_walls = True
    parameters.reinforcement_mesh_required = bool(mesh_required)
    parameters.mesh_allowance_percentage = float(mesh_allowance_percentage)

    # The existing stage/material engine uses the user-selected wall
    # thickness as its deterministic construction input. The AI's
    # individual wall thicknesses remain available in wall_thicknesses_m.
    parameters.sources.update(
        {
            "wall_height": "User supplied",
            "wall_thickness": "User supplied",
            "foundation_width": "User supplied",
            "foundation_depth": "User supplied",
            "slab_thickness": "User supplied",
            "hardcore_depth": "User supplied",
            "reinforcement_runs": "User supplied",
            "brick_force_interval": "User supplied",
            "reinforcement_mesh": "User supplied",
            "mesh_allowance": "User supplied",
        }
    )

    # ConstructionParameters currently stores wall thicknesses as a list
    # because Vision can detect more than one wall thickness. The stage
    # quantity engine needs one deterministic wall thickness input.
    parameters.wall_thicknesses_m = [float(wall_thickness_m)]

    return parameters


# ----------------------------------------------------------------------
# Stage material handling
# ----------------------------------------------------------------------


def _add_openings_to_walls_stage(
    stages: list[Any],
    building: Any,
) -> None:
    """Put Vision-detected windows and doors into the Walls stage."""

    for stage in stages:
        if getattr(stage, "stage_number", None) != 2:
            continue

        window_count = int(getattr(building, "window_count", 0) or 0)
        door_count = int(getattr(building, "door_count", 0) or 0)

        if window_count > 0:
            stage.materials.append(
                CalculatedMaterial(
                    material_name="Windows",
                    quantity=float(window_count),
                    unit="unit",
                    basis="AI Vision-detected window count",
                )
            )

        if door_count > 0:
            stage.materials.append(
                CalculatedMaterial(
                    material_name="Doors",
                    quantity=float(door_count),
                    unit="unit",
                    basis="AI Vision-detected door count",
                )
            )

        return


def _material_id_from_name(material_name: str) -> str | None:
    """Resolve a frontend-friendly material ID without duplicating pricing logic."""

    try:
        pricing_module = importlib.import_module(
            "backend.services.pricing_integration_service"
        )
        mapping = getattr(pricing_module, "MATERIAL_NAME_MAP", {})
        return mapping.get(material_name)
    except Exception:
        return None


# ----------------------------------------------------------------------
# Stage serialisation
# ----------------------------------------------------------------------


def _serialize_stage_results(stage_results: list[Any]) -> list[dict[str, Any]]:
    """
    Convert the ACTIVE StagePricingResult structure into the response
    expected by the frontend.
    """

    ordered = sorted(
        stage_results,
        key=lambda stage: DISPLAY_STAGE_ORDER.get(
            stage.stage_number,
            99,
        ),
    )

    result: list[dict[str, Any]] = []

    for stage in ordered:
        display_stage = DISPLAY_STAGE_ORDER.get(
            stage.stage_number,
            stage.stage_number,
        )
        display_name = DISPLAY_STAGE_NAMES.get(
            display_stage,
            stage.stage_name,
        )

        cost_summary = getattr(stage, "cost_summary", None)
        cost_lines = getattr(cost_summary, "material_costs", []) or []

        materials: list[dict[str, Any]] = []

        for material_cost in cost_lines:
            name = getattr(
                material_cost,
                "material_name",
                getattr(material_cost, "name", ""),
            )
            quantity = float(getattr(material_cost, "quantity", 0.0) or 0.0)
            unit = getattr(material_cost, "unit", "")
            unit_price = float(
                getattr(material_cost, "unit_price", 0.0) or 0.0
            )
            total_cost = float(
                getattr(
                    material_cost,
                    "material_cost",
                    getattr(material_cost, "total_cost", 0.0),
                )
                or 0.0
            )

            materials.append(
                {
                    "material_id": _material_id_from_name(name),
                    "material_name": name,
                    "quantity": round(quantity, 4),
                    "unit": unit,
                    "unit_price": round(unit_price, 4),
                    "total_cost": round(total_cost, 2),
                }
            )

        material_subtotal = float(getattr(stage, "subtotal", 0.0) or 0.0)
        labour_cost = float(getattr(stage, "labour_cost", 0.0) or 0.0)
        labour_percentage = float(
            getattr(stage, "labour_percentage", 0.0) or 0.0
        )
        transport_cost = float(
            getattr(stage, "transport_cost", 0.0) or 0.0
        )
        stage_total = float(getattr(stage, "stage_total", 0.0) or 0.0)

        result.append(
            {
                "stage_number": display_stage,
                "stage_name": display_name,
                "materials": materials,
                "material_subtotal": round(material_subtotal, 2),
                "labour_cost": round(labour_cost, 2),
                "labour_percentage": round(labour_percentage, 2),
                "transport_cost": round(transport_cost, 2),
                "stage_total": round(stage_total, 2),
            }
        )

    return result


# ----------------------------------------------------------------------
# Public API information
# ----------------------------------------------------------------------


@router.get("/")
def estimation_info() -> Dict[str, Any]:
    return {
        "service": "ZimBuild AI Construction Estimation",
        "status": "available",
        "pipeline": "new_ai_visualisation_pipeline",
        "project_type": "residential",
        "roof_detection": False,
        "roofing_estimation": False,
        "supported_stages": [
            "Foundation / Footing",
            "Slab",
            "Walls",
            "Reinforcement",
        ],
        "labour_rate": 0.12,
        "transport_rate": 0.04,
        "location_factors": {
            "city_town": 1.20,
            "growth_point": 1.00,
            "rural_farm": 0.80,
        },
        "scale_mode": "user_selected_architectural_scale",
        "supported_scales": ["1:50", "1:100", "1:200", "1:500"],
    }


# ----------------------------------------------------------------------
# Lightweight calculation endpoint
# ----------------------------------------------------------------------


@router.post("/calculate/{processed_filename}")
def calculate_estimation(
    processed_filename: str,
    scale_ratio: float = Query(100, gt=0),
    wall_height_m: float = Query(2.7, gt=0),
    wall_thickness_m: float = Query(0.2, gt=0),
    wastage_percentage: float = Query(5.0, ge=0),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run the new AI visualiser and return Vision + building quantities."""

    del threshold  # The new Vision analyser does not use the old wall threshold.

    _assert_plan_owner(processed_filename, current_user)
    processed_path = _get_processed_plan_path(processed_filename)
    started_at = time.perf_counter()

    try:
        _debug_log("[1/4] STARTING NEW AI VISUALISATION...", started_at)
        analysis_result = _run_new_ai_visualiser(
            processed_path,
            scale_ratio,
        )
        _validate_vision_result(analysis_result)
        _debug_log("[1/4] AI VISUALISATION COMPLETE.", started_at)

        parameters = _build_construction_parameters(
            analysis_result,
            wall_height_m=wall_height_m,
            wall_thickness_m=wall_thickness_m,
            foundation_width_m=0.3,
            foundation_depth_m=0.4,
            slab_thickness_m=0.3,
            hardcore_depth_m=0.3,
            reinforcement_runs=3,
            brick_force_interval_courses=4,
            mesh_required=True,
            mesh_allowance_percentage=10.0,
        )

        building = calculate_building_quantities(parameters)

        return _json_safe(
            {
                "status": "estimated",
                "pipeline": "new_ai_visualisation_pipeline",
                "scale": {
                    "scale_ratio": scale_ratio,
                    "scale_label": f"1:{int(scale_ratio) if float(scale_ratio).is_integer() else scale_ratio:g}",
                },
                "construction_parameters": parameters,
                "phase8": analysis_result,
                "phase9": building,
            }
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _debug_log(f"CALCULATION FAILED: {exc}", started_at)
        raise HTTPException(
            status_code=500,
            detail=f"Estimation failed: {exc}",
        ) from exc


# ----------------------------------------------------------------------
# Complete estimation endpoint
# ----------------------------------------------------------------------


@router.post("/full/{processed_filename}")
def full_estimation(
    processed_filename: str,
    project_name: str = Query(..., min_length=1),
    location: str = Query(..., min_length=1),
    scale_ratio: float = Query(100, gt=0),
    wall_height_m: float = Query(2.7, gt=0),
    wall_thickness_m: float = Query(0.2, gt=0),
    foundation_width_m: float = Query(0.3, gt=0),
    foundation_depth_m: float = Query(0.4, gt=0),
    slab_thickness_m: float = Query(0.3, gt=0),
    hardcore_depth_m: float = Query(0.3, gt=0),
    wastage_percentage: float = Query(5.0, ge=0),
    reinforcement_runs: int = Query(3, ge=1),
    brick_force_interval_courses: int = Query(4, ge=1),
    mesh_required: bool = Query(True),
    mesh_allowance_percentage: float = Query(10.0, ge=0),
    location_profile_id: str = Query("growth_point", min_length=1),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    currency: str = Query("USD", min_length=1),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Run the complete NEW AI visualisation -> BoQ/cost pipeline.

    The selected architectural scale is passed directly to the new Vision
    analyser. No old Phase 8/Light-U-Net quantity adapter is used here.
    """

    del threshold  # Kept only for backwards-compatible frontend/API calls.

    started_at = time.perf_counter()
    _assert_plan_owner(processed_filename, current_user)
    processed_path = _get_processed_plan_path(processed_filename)
    normalised_location = _normalise_location_profile(location_profile_id)

    _debug_log("REQUEST RECEIVED: new full estimation started.", started_at)
    _debug_log(
        f"Project={project_name!r} | Location={location!r} | "
        f"Processed plan={processed_filename!r}",
        started_at,
    )
    _debug_log(
        f"Scale=1:{scale_ratio:g} | Wall height={wall_height_m}m | "
        f"Foundation={foundation_width_m}m x {foundation_depth_m}m | "
        f"Slab={slab_thickness_m}m | Hardcore={hardcore_depth_m}m",
        started_at,
    )

    # ==============================================================
    # 1. NEW AI VISUALISATION
    # ==============================================================

    try:
        _debug_log(
            "[1/10] RUNNING NEW AI VISUALISER...",
            started_at,
        )

        analysis_result = _run_new_ai_visualiser(
            processed_path,
            scale_ratio,
        )

        _validate_vision_result(analysis_result)

        _debug_log(
            "[1/10] AI VISUALISATION COMPLETED.",
            started_at,
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _debug_log(f"[1/10] FAILED: AI visualisation: {exc}", started_at)
        raise HTTPException(
            status_code=500,
            detail=f"AI visualisation failed: {exc}",
        ) from exc

    # ==============================================================
    # 2. CONSTRUCTION PARAMETERS
    # ==============================================================

    try:
        _debug_log(
            "[2/10] BUILDING CONSTRUCTION PARAMETERS...",
            started_at,
        )

        construction_parameters = _build_construction_parameters(
            analysis_result,
            wall_height_m=wall_height_m,
            wall_thickness_m=wall_thickness_m,
            foundation_width_m=foundation_width_m,
            foundation_depth_m=foundation_depth_m,
            slab_thickness_m=slab_thickness_m,
            hardcore_depth_m=hardcore_depth_m,
            reinforcement_runs=reinforcement_runs,
            brick_force_interval_courses=brick_force_interval_courses,
            mesh_required=mesh_required,
            mesh_allowance_percentage=mesh_allowance_percentage,
        )

        _debug_log(
            "[2/10] CONSTRUCTION PARAMETERS READY.",
            started_at,
        )

    except Exception as exc:
        _debug_log(
            f"[2/10] FAILED: construction parameters: {exc}",
            started_at,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Construction parameter preparation failed: {exc}",
        ) from exc

    # ==============================================================
    # 3. BUILDING QUANTITIES
    # ==============================================================

    try:
        _debug_log(
            "[3/10] CALCULATING BUILDING QUANTITIES...",
            started_at,
        )

        building = calculate_building_quantities(
            construction_parameters
        )

        _debug_log(
            f"[3/10] BUILDING QUANTITIES READY: "
            f"floor_area={getattr(building, 'floor_area_m2', None)} | "
            f"wall_length={getattr(building, 'total_wall_length_m', None)}",
            started_at,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _debug_log(
            f"[3/10] FAILED: building quantities: {exc}",
            started_at,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Building quantity calculation failed: {exc}",
        ) from exc

    # ==============================================================
    # 4. MATERIAL QUANTITIES / FOUR STAGES
    # ==============================================================

    try:
        _debug_log(
            "[4/10] CALCULATING MATERIAL QUANTITIES AND STAGES...",
            started_at,
        )

        stages = calculate_all_stages(
            building,
            construction_parameters,
        )

        _add_openings_to_walls_stage(
            stages,
            building,
        )

        _debug_log(
            f"[4/10] MATERIAL STAGES READY: {len(stages)} stages.",
            started_at,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _debug_log(
            f"[4/10] FAILED: material quantities: {exc}",
            started_at,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Material quantity calculation failed: {exc}",
        ) from exc

    # ==============================================================
    # 5. MATERIAL PRICING
    # ==============================================================

    try:
        _debug_log(
            "[5/10] PRICING MATERIALS STAGE BY STAGE...",
            started_at,
        )

        pricing_results = price_all_stages(
            stages=stages,
            location_profile_id=normalised_location,
        )

        _debug_log(
            "[5/10] MATERIAL PRICING COMPLETED.",
            started_at,
        )

    except Exception as exc:
        _debug_log(
            f"[5/10] FAILED: material pricing: {exc}",
            started_at,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Material pricing failed: {exc}",
        ) from exc

    # ==============================================================
    # 6. LABOUR
    # ==============================================================

    try:
        _debug_log(
            "[6/10] APPLYING 12% LABOUR...",
            started_at,
        )

        labour_total = apply_labour_to_stage_results(
            pricing_results
        )

        _debug_log(
            f"[6/10] LABOUR COMPLETE: ${labour_total:,.2f}",
            started_at,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Labour calculation failed: {exc}",
        ) from exc

    # ==============================================================
    # 7. TRANSPORT
    # ==============================================================

    try:
        _debug_log(
            "[7/10] APPLYING 4% STAGE TRANSPORT...",
            started_at,
        )

        transport_total = calculate_stage_transport(
            pricing_results
        )

        _debug_log(
            f"[7/10] TRANSPORT COMPLETE: ${transport_total:,.2f}",
            started_at,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Transport calculation failed: {exc}",
        ) from exc

    # ==============================================================
    # 8. LOCATION
    # ==============================================================

    try:
        location_factor = _location_factor(normalised_location)
        location_name = _location_name(normalised_location)
    except HTTPException:
        raise

    _debug_log(
        f"[8/10] LOCATION: {location_name} x{location_factor:.2f}",
        started_at,
    )

    # ==============================================================
    # 9. PROJECT TOTALS
    # ==============================================================

    material_subtotal = calculate_overall_material_subtotal(
        pricing_results
    )

    base_project_cost, final_project_cost = calculate_location_adjusted_total(
        material_subtotal=material_subtotal,
        labour_total=labour_total,
        transport_total=transport_total,
        location_factor=location_factor,
    )

    _debug_log(
        f"[9/10] TOTALS: materials=${material_subtotal:,.2f} | "
        f"labour=${labour_total:,.2f} | "
        f"transport=${transport_total:,.2f} | "
        f"base=${base_project_cost:,.2f} | "
        f"final=${final_project_cost:,.2f}",
        started_at,
    )

    # ==============================================================
    # 10. FRONTEND / BOQ SERIALISATION
    # ==============================================================

    stage_results = _serialize_stage_results(
        pricing_results
    )

    all_materials: list[dict[str, Any]] = []

    for stage in stage_results:
        for material in stage["materials"]:
            all_materials.append(
                {
                    "item_number": str(len(all_materials) + 1),
                    "description": material["material_name"],
                    "material_name": material["material_name"],
                    "quantity": material["quantity"],
                    "unit": material["unit"],
                    "unit_rate": material["unit_price"],
                    "unit_price": material["unit_price"],
                    "amount": material["total_cost"],
                    "total_cost": material["total_cost"],
                    "stage_number": stage["stage_number"],
                    "stage_name": stage["stage_name"],
                }
            )

    construction_summary = {
        "floor_area_m2": getattr(building, "floor_area_m2", None),
        "wall_count": getattr(building, "wall_count", None),
        "total_wall_length_m": getattr(
            building,
            "total_wall_length_m",
            None,
        ),
        "external_wall_length_m": getattr(
            building,
            "external_wall_length_m",
            None,
        ),
        "internal_wall_length_m": getattr(
            building,
            "internal_wall_length_m",
            None,
        ),
        "wall_height_m": wall_height_m,
        "wall_thickness_m": wall_thickness_m,
        "room_count": getattr(building, "room_count", None),
        "door_count": getattr(building, "door_count", None),
        "window_count": getattr(building, "window_count", None),
    }

    response = {
        "status": "completed",
        "pipeline": "new_ai_visualisation_pipeline",
        "project": {
            "project_name": project_name,
            "location": location,
            "currency": currency,
            "project_type": "residential",
        },
        "scale": {
            "scale_ratio": scale_ratio,
            "scale_label": (
                f"1:{int(scale_ratio)}"
                if float(scale_ratio).is_integer()
                else f"1:{scale_ratio:g}"
            ),
            "source": "User selected architectural scale passed to AI visualiser",
        },
        "parameters": {
            "wall_height_m": wall_height_m,
            "wall_thickness_m": wall_thickness_m,
            "foundation_width_m": foundation_width_m,
            "foundation_depth_m": foundation_depth_m,
            "slab_thickness_m": slab_thickness_m,
            "hardcore_depth_m": hardcore_depth_m,
            "wastage_percentage": wastage_percentage,
            "reinforcement_runs": reinforcement_runs,
            "brick_force_interval_courses": brick_force_interval_courses,
            "mesh_required": mesh_required,
            "mesh_allowance_percentage": mesh_allowance_percentage,
            "location_profile_id": normalised_location,
            "location_factor": location_factor,
        },
        "analysis": {
            "analysis_status": analysis_result.get("analysis_status", "success"),
            "floor_area_m2": analysis_result.get("floor", {}).get(
                "recommended_floor_area_m2"
            ),
            "wall_count": analysis_result.get("walls", {}).get("count", 0),
            "external_wall_count": len(
                analysis_result.get("walls", {}).get("external_walls", []) or []
            ),
            "internal_wall_count": len(
                analysis_result.get("walls", {}).get("internal_walls", []) or []
            ),
            "total_wall_length_m": analysis_result.get("walls", {}).get(
                "total_wall_length_m"
            ),
            "room_count": analysis_result.get("rooms", {}).get("count", 0),
            "door_count": analysis_result.get("doors", {}).get("count", 0),
            "window_count": analysis_result.get("windows", {}).get("count", 0),
            "roof_present": analysis_result.get("roof", {}).get("present", False),
            "roof_detection": False,
            "roofing_estimation": False,
            "construction_stages": [
                "Foundation / Footing",
                "Slab",
                "Walls",
                "Reinforcement",
            ],
        },
        "construction_summary": construction_summary,
        "phase8": _json_safe(analysis_result),
        "phase9": {
            "status": "completed",
            "building": _json_safe(building),
            "summary": construction_summary,
        },
        "phase10": {
            "status": "completed",
            "materials": all_materials,
            "stages": stage_results,
        },
        "phase11": {
            "status": "completed",
            "stages": stage_results,
            "material_subtotal": round(material_subtotal, 2),
            "labour_total": round(labour_total, 2),
            "transport_total": round(transport_total, 2),
            "base_project_cost": round(base_project_cost, 2),
            "location": {
                "id": normalised_location,
                "name": location_name,
                "factor": location_factor,
            },
            "final_project_cost": round(final_project_cost, 2),
            "grand_total": round(final_project_cost, 2),
        },
        "phase12": {
            "status": "completed",
            "items": all_materials,
            "material_subtotal": round(material_subtotal, 2),
            "labour_total": round(labour_total, 2),
            "transport_total": round(transport_total, 2),
            "base_project_cost": round(base_project_cost, 2),
            "location": location_name,
            "final_estimated_cost": round(final_project_cost, 2),
            "grand_total": round(final_project_cost, 2),
            "currency": currency,
        },
        "totals": {
            "materials": round(material_subtotal, 2),
            "labour": round(labour_total, 2),
            "transport": round(transport_total, 2),
            "base_project_cost": round(base_project_cost, 2),
            "location_factor": location_factor,
            "final_estimated_cost": round(final_project_cost, 2),
            "grand_total": round(final_project_cost, 2),
        },
    }

    _debug_log(
        "[10/10] RESPONSE READY. New AI visualisation pipeline completed.",
        started_at,
    )

    safe_response = _json_safe(response)

    # Save the completed BoQ/cost result in PostgreSQL and associate it
    # with the uploaded plan record using the stable stored filename.
    try:
        with Session(engine) as db:
            plan_record = (
                db.query(Plan)
                .filter(Plan.stored_filename == processed_filename)
                .one_or_none()
            )

            # Keep older uploads usable if they predate database tracking.
            if plan_record is None:
                plan_record = Plan(
                    original_filename=processed_filename,
                    stored_filename=processed_filename,
                    status="estimated",
                )
                db.add(plan_record)
                db.flush()

            estimate_record = Estimate(
                plan_id=plan_record.id,
                total_cost=float(final_project_cost),
                currency=currency,
                results=safe_response,
            )
            db.add(estimate_record)
            plan_record.status = "estimated"
            db.commit()
            db.refresh(estimate_record)

            safe_response["database"] = {
                "saved": True,
                "plan_id": plan_record.id,
                "estimate_id": estimate_record.id,
            }

    except Exception as exc:
        _debug_log(
            f"FAILED TO SAVE ESTIMATION TO POSTGRESQL: {exc}",
            started_at,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "The estimation was calculated, but the result could not "
                "be saved to PostgreSQL."
            ),
        ) from exc

    return safe_response
