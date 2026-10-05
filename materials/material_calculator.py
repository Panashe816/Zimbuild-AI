"""
ZimBuild AI - Material Calculator
=================================

Phase 10 material calculation engine.

This module converts building quantities into construction-material
quantities.

Important compatibility note
----------------------------
The project contains two legacy calculation modules:

    materials.wall_materials
    materials.mortar

Both modules were written against an older MaterialQuantity model
which contains fields such as:

    wastage_percentage

The current materials.models.MaterialQuantity model is newer and
does not contain that field.

Therefore this file provides a compatibility layer for BOTH legacy
modules. The frozen modules themselves are not modified.

User-facing materials include:

    - Standard brick
    - Cement
    - Building sand
    - Quarry stone
    - Construction water
    - Fibre-cement roofing sheet, when applicable
    - Timber pole, when applicable

Mortar remains an internal calculation and is not displayed as a
separate material.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, List, Optional

from estimation.models import BuildingQuantitySummary
from materials.models import (
    MasonryParameters,
    MaterialQuantity,
)


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_QUARRY_STONE_VOLUME_M3 = 0.0
DEFAULT_WATER_ALLOWANCE_LITRES = 0.0


# ============================================================================
# LEGACY COMPATIBILITY MATERIAL QUANTITY
# ============================================================================

class _LegacyMaterialQuantity:
    """
    Compatibility replacement for the old MaterialQuantity class.

    This class intentionally accepts arbitrary keyword arguments because
    the frozen legacy modules may still pass fields which no longer exist
    in the current materials.models.MaterialQuantity.

    Examples of legacy fields include:

        wastage_percentage
        material_id
        category
        source

    Nothing in this class changes the current project model.
    It exists only temporarily while executing legacy functions.
    """

    def __init__(
        self,
        material_name: str = "",
        quantity: float = 0.0,
        unit: str = "",
        **kwargs: Any,
    ) -> None:

        self.material_name = material_name
        self.quantity = quantity
        self.unit = unit

        # Preserve every additional legacy field.
        for key, value in kwargs.items():
            setattr(self, key, value)


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _safe_non_negative(
    value: Optional[float],
) -> float:
    """
    Convert a value to a non-negative float.

    Invalid or missing values become zero.
    """

    if value is None:
        return 0.0

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, numeric_value)


def _apply_wastage(
    quantity: float,
    wastage_percentage: float,
) -> float:
    """
    Apply wastage percentage to a quantity.
    """

    quantity = _safe_non_negative(quantity)

    try:
        wastage = float(wastage_percentage)
    except (TypeError, ValueError):
        wastage = 0.0

    wastage = max(0.0, wastage)

    return quantity * (
        1.0 + wastage / 100.0
    )


def _round_quantity(
    quantity: float,
    decimals: int = 3,
) -> float:
    """
    Safely round a quantity.
    """

    quantity = _safe_non_negative(quantity)

    if quantity <= 0:
        return 0.0

    return round(quantity, decimals)


def _extract_quantity(
    value: Any,
) -> float:
    """
    Extract a numeric quantity from either:

        - a number
        - a legacy MaterialQuantity
        - a current MaterialQuantity
        - an object exposing quantity

    """

    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return _safe_non_negative(value)

    quantity = getattr(
        value,
        "quantity",
        0.0,
    )

    return _safe_non_negative(quantity)


def _extract_material_name(
    value: Any,
    default: str = "",
) -> str:
    """
    Extract a material name defensively.
    """

    if value is None:
        return default

    name = getattr(
        value,
        "material_name",
        default,
    )

    if name is None:
        return default

    return str(name)


def _extract_material_unit(
    value: Any,
    default: str = "",
) -> str:
    """
    Extract a material unit defensively.
    """

    if value is None:
        return default

    unit = getattr(
        value,
        "unit",
        default,
    )

    if unit is None:
        return default

    return str(unit)


def _add_material(
    materials: List[MaterialQuantity],
    material_name: str,
    quantity: float,
    unit: str,
    material_id: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Add a current-model MaterialQuantity to the result list.

    Materials with zero quantity are not added.
    """

    quantity = _safe_non_negative(quantity)

    if quantity <= 0:
        return

    materials.append(
        MaterialQuantity(
            material_name=material_name,
            quantity=_round_quantity(quantity),
            unit=unit,
            material_id=material_id,
            category=category,
            source=source,
            metadata=metadata or {},
        )
    )


# ============================================================================
# WALL MATERIALS COMPATIBILITY
# ============================================================================

def _create_wall_material_parameters(
    masonry_parameters: MasonryParameters,
) -> SimpleNamespace:
    """
    Convert the current MasonryParameters names to the legacy names
    expected by materials.wall_materials.
    """

    return SimpleNamespace(

        # Current:
        #     brick_length_m
        #
        # Legacy:
        #     unit_length_m
        unit_length_m=float(
            getattr(
                masonry_parameters,
                "brick_length_m",
                0.230,
            )
        ),

        # Current:
        #     brick_height_m
        #
        # Legacy:
        #     unit_height_m
        unit_height_m=float(
            getattr(
                masonry_parameters,
                "brick_height_m",
                0.076,
            )
        ),

        # Current:
        #     brick_thickness_m
        #
        # Legacy:
        #     unit_thickness_m
        unit_thickness_m=float(
            getattr(
                masonry_parameters,
                "brick_thickness_m",
                0.110,
            )
        ),

        wall_thickness_m=float(
            getattr(
                masonry_parameters,
                "wall_thickness_m",
                0.200,
            )
        ),

        # Current:
        #     mortar_joint_m
        #
        # Legacy:
        #     mortar_joint_thickness_m
        mortar_joint_thickness_m=float(
            getattr(
                masonry_parameters,
                "mortar_joint_m",
                0.010,
            )
        ),

        wastage_percentage=float(
            getattr(
                masonry_parameters,
                "wastage_percentage",
                5.0,
            )
        ),
    )


def _calculate_bricks_legacy_compatible(
    wall_area_m2: float,
    masonry_parameters: MasonryParameters,
) -> Any:
    """
    Execute the frozen wall_materials.calculate_bricks_required()
    function using a temporary legacy-compatible MaterialQuantity.

    The actual wall_materials.py source is NOT modified.
    """

    import materials.wall_materials as wall_materials_module

    original_material_quantity = getattr(
        wall_materials_module,
        "MaterialQuantity",
        None,
    )

    try:

        # Give the legacy module the compatibility constructor.
        wall_materials_module.MaterialQuantity = (
            _LegacyMaterialQuantity
        )

        legacy_parameters = (
            _create_wall_material_parameters(
                masonry_parameters
            )
        )

        return wall_materials_module.calculate_bricks_required(
            wall_area_m2=wall_area_m2,
            parameters=legacy_parameters,
        )

    finally:

        # Always restore the original object.
        if original_material_quantity is not None:
            wall_materials_module.MaterialQuantity = (
                original_material_quantity
            )


# ============================================================================
# MORTAR COMPATIBILITY
# ============================================================================

def _calculate_mortar_materials_legacy_compatible(
    mortar_volume_m3: float,
) -> Any:
    """
    Execute the frozen mortar.calculate_mortar_materials() function
    using the temporary legacy-compatible MaterialQuantity.

    This is the second compatibility layer.

    The previous implementation only protected wall_materials.py.
    This function also protects mortar.py from the old
    wastage_percentage constructor argument.
    """

    import materials.mortar as mortar_module

    original_material_quantity = getattr(
        mortar_module,
        "MaterialQuantity",
        None,
    )

    try:

        # Give the legacy mortar module a constructor that accepts
        # all of its old keyword arguments.
        mortar_module.MaterialQuantity = (
            _LegacyMaterialQuantity
        )

        return mortar_module.calculate_mortar_materials(
            mortar_volume_m3=mortar_volume_m3,
        )

    finally:

        # Restore the current MaterialQuantity after execution.
        if original_material_quantity is not None:
            mortar_module.MaterialQuantity = (
                original_material_quantity
            )


# ============================================================================
# MORTAR VOLUME
# ============================================================================

def calculate_mortar_volume(
    wall_volume_m3: float,
    brick_quantity: float,
    parameters: MasonryParameters,
) -> float:
    """
    Calculate the internal mortar volume.

    Formula:

        mortar volume =
            wall volume - total brick volume

    Wastage is then applied.

    Mortar itself is NOT returned as a user-facing material.
    """

    wall_volume_m3 = _safe_non_negative(
        wall_volume_m3
    )

    brick_quantity = _safe_non_negative(
        brick_quantity
    )

    if (
        wall_volume_m3 <= 0
        or brick_quantity <= 0
    ):
        return 0.0

    brick_length = _safe_non_negative(
        getattr(
            parameters,
            "brick_length_m",
            0.230,
        )
    )

    brick_height = _safe_non_negative(
        getattr(
            parameters,
            "brick_height_m",
            0.076,
        )
    )

    brick_thickness = _safe_non_negative(
        getattr(
            parameters,
            "brick_thickness_m",
            0.110,
        )
    )

    brick_volume_m3 = (
        brick_length
        * brick_height
        * brick_thickness
    )

    total_brick_volume_m3 = (
        brick_quantity
        * brick_volume_m3
    )

    mortar_volume_m3 = max(
        0.0,
        wall_volume_m3
        - total_brick_volume_m3,
    )

    mortar_volume_m3 = _apply_wastage(
        mortar_volume_m3,
        getattr(
            parameters,
            "wastage_percentage",
            5.0,
        ),
    )

    return mortar_volume_m3


# ============================================================================
# BASELINE MATERIALS
# ============================================================================

def calculate_quarry_stone_quantity(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
) -> float:
    """
    Return the explicitly supplied quarry-stone quantity.

    The architectural plan alone does not provide sufficient structural
    information to invent a concrete aggregate quantity.

    Therefore the system uses the project/site allowance when supplied.
    """

    explicit_quantity = getattr(
        masonry_parameters,
        "quarry_stone_volume_m3",
        None,
    )

    if explicit_quantity is not None:
        return _safe_non_negative(
            explicit_quantity
        )

    return DEFAULT_QUARRY_STONE_VOLUME_M3


def calculate_construction_water_quantity(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
) -> float:
    """
    Return the explicitly supplied construction-water allowance.
    """

    explicit_quantity = getattr(
        masonry_parameters,
        "water_allowance_litres",
        None,
    )

    if explicit_quantity is not None:
        return _safe_non_negative(
            explicit_quantity
        )

    return DEFAULT_WATER_ALLOWANCE_LITRES


# ============================================================================
# ROOFING MATERIALS
# ============================================================================

def calculate_roofing_materials(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
) -> List[MaterialQuantity]:
    """
    Calculate roofing materials only when roof information exists.

    No roofing material is invented when the architectural plan has
    no detected/present roof.
    """

    materials: List[MaterialQuantity] = []

    roof_present = bool(
        getattr(
            quantity_summary,
            "roof_present",
            False,
        )
    )

    roof_area_m2 = _safe_non_negative(
        getattr(
            quantity_summary,
            "roof_area_m2",
            0.0,
        )
    )

    if (
        not roof_present
        or roof_area_m2 <= 0
    ):
        return materials

    # ------------------------------------------------------------------
    # Fibre-cement roofing sheets
    # ------------------------------------------------------------------

    sheet_coverage_m2 = _safe_non_negative(
        getattr(
            masonry_parameters,
            "roof_sheet_coverage_m2",
            None,
        )
    )

    if sheet_coverage_m2 > 0:

        sheet_quantity = math.ceil(
            roof_area_m2
            / sheet_coverage_m2
        )

        sheet_quantity = math.ceil(
            _apply_wastage(
                sheet_quantity,
                getattr(
                    masonry_parameters,
                    "wastage_percentage",
                    5.0,
                ),
            )
        )

        _add_material(
            materials=materials,
            material_name=(
                "Fibre-cement roofing sheet"
            ),
            quantity=sheet_quantity,
            unit="sheet",
            material_id="fibre_cement_sheet",
            category="Roofing",
            source=(
                "Roof area and sheet coverage"
            ),
            metadata={
                "roof_area_m2": roof_area_m2,
                "sheet_coverage_m2": (
                    sheet_coverage_m2
                ),
            },
        )

    # ------------------------------------------------------------------
    # Timber poles
    # ------------------------------------------------------------------

    timber_length_m = _safe_non_negative(
        getattr(
            masonry_parameters,
            "roof_timber_length_m",
            None,
        )
    )

    timber_spacing_m = _safe_non_negative(
        getattr(
            masonry_parameters,
            "timber_spacing_m",
            None,
        )
    )

    if (
        timber_length_m > 0
        and timber_spacing_m > 0
    ):

        pole_quantity = math.ceil(
            timber_length_m
            / timber_spacing_m
        )

        pole_quantity = math.ceil(
            _apply_wastage(
                pole_quantity,
                getattr(
                    masonry_parameters,
                    "wastage_percentage",
                    5.0,
                ),
            )
        )

        _add_material(
            materials=materials,
            material_name="Timber pole",
            quantity=pole_quantity,
            unit="pole",
            material_id="timber_pole_6m",
            category="Timber",
            source=(
                "Roof timber length and spacing"
            ),
            metadata={
                "roof_timber_length_m": (
                    timber_length_m
                ),
                "timber_spacing_m": (
                    timber_spacing_m
                ),
            },
        )

    return materials


# ============================================================================
# MAIN BUILDING MATERIAL CALCULATOR
# ============================================================================

def calculate_building_materials(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
) -> List[MaterialQuantity]:
    """
    Convert building quantities into construction materials.

    Returns current-model MaterialQuantity objects.

    Mortar is calculated internally but is never returned directly.
    """

    if quantity_summary is None:
        raise ValueError(
            "quantity_summary is required."
        )

    if masonry_parameters is None:
        raise ValueError(
            "masonry_parameters is required."
        )

    materials: List[MaterialQuantity] = []

    # ==================================================================
    # 1. STANDARD BRICKS
    # ==================================================================

    net_wall_area = _safe_non_negative(
        getattr(
            quantity_summary,
            "total_net_wall_area_m2",
            0.0,
        )
    )

    legacy_brick_result = (
        _calculate_bricks_legacy_compatible(
            wall_area_m2=net_wall_area,
            masonry_parameters=masonry_parameters,
        )
    )

    brick_quantity = _extract_quantity(
        legacy_brick_result
    )

    if brick_quantity > 0:

        _add_material(
            materials=materials,
            material_name="Standard brick",
            quantity=math.ceil(
                brick_quantity
            ),
            unit="brick",
            material_id="standard_brick",
            category="Masonry",
            source="Net wall area",
            metadata={
                "net_wall_area_m2": (
                    net_wall_area
                ),
                "wastage_percentage": (
                    getattr(
                        masonry_parameters,
                        "wastage_percentage",
                        5.0,
                    )
                ),
            },
        )

    # ==================================================================
    # 2. INTERNAL MORTAR CALCULATION
    # ==================================================================

    wall_volume_m3 = _safe_non_negative(
        getattr(
            quantity_summary,
            "total_wall_volume_m3",
            0.0,
        )
    )

    mortar_volume_m3 = (
        calculate_mortar_volume(
            wall_volume_m3=wall_volume_m3,
            brick_quantity=brick_quantity,
            parameters=masonry_parameters,
        )
    )

    # ==================================================================
    # 3. CEMENT + BUILDING SAND
    # ==================================================================

    if mortar_volume_m3 > 0:

        legacy_mortar_results = (
            _calculate_mortar_materials_legacy_compatible(
                mortar_volume_m3=mortar_volume_m3
            )
        )

        # The frozen mortar module may return a tuple/list containing
        # cement and sand quantities.
        cement_result = None
        sand_result = None

        if isinstance(
            legacy_mortar_results,
            (tuple, list),
        ):

            if len(
                legacy_mortar_results
            ) >= 1:
                cement_result = (
                    legacy_mortar_results[0]
                )

            if len(
                legacy_mortar_results
            ) >= 2:
                sand_result = (
                    legacy_mortar_results[1]
                )

        else:

            # Defensive support if the legacy function returns
            # an object containing cement and sand attributes.
            cement_result = getattr(
                legacy_mortar_results,
                "cement",
                None,
            )

            sand_result = getattr(
                legacy_mortar_results,
                "sand",
                None,
            )

        # --------------------------------------------------------------
        # Cement
        # --------------------------------------------------------------

        if cement_result is not None:

            cement_quantity = (
                _extract_quantity(
                    cement_result
                )
            )

            if cement_quantity > 0:

                _add_material(
                    materials=materials,
                    material_name="Cement",
                    quantity=cement_quantity,
                    unit="bag",
                    material_id="cement_50kg",
                    category="Cement",
                    source=(
                        "Internal mortar calculation"
                    ),
                    metadata={
                        "mortar_volume_m3": (
                            mortar_volume_m3
                        ),
                    },
                )

        # --------------------------------------------------------------
        # Building sand
        # --------------------------------------------------------------

        if sand_result is not None:

            sand_quantity = (
                _extract_quantity(
                    sand_result
                )
            )

            if sand_quantity > 0:

                _add_material(
                    materials=materials,
                    material_name="Building sand",
                    quantity=sand_quantity,
                    unit="m3",
                    material_id="building_sand",
                    category="Aggregates",
                    source=(
                        "Internal mortar calculation"
                    ),
                    metadata={
                        "mortar_volume_m3": (
                            mortar_volume_m3
                        ),
                    },
                )

    # ==================================================================
    # 4. QUARRY STONE
    # ==================================================================

    quarry_stone_quantity = (
        calculate_quarry_stone_quantity(
            quantity_summary=quantity_summary,
            masonry_parameters=masonry_parameters,
        )
    )

    _add_material(
        materials=materials,
        material_name="Quarry stone",
        quantity=quarry_stone_quantity,
        unit="m3",
        material_id="quarry_stone",
        category="Aggregates",
        source="Project/site allowance",
        metadata={
            "baseline_material": True,
        },
    )

    # ==================================================================
    # 5. CONSTRUCTION WATER
    # ==================================================================

    water_quantity = (
        calculate_construction_water_quantity(
            quantity_summary=quantity_summary,
            masonry_parameters=masonry_parameters,
        )
    )

    _add_material(
        materials=materials,
        material_name="Construction water",
        quantity=water_quantity,
        unit="litres",
        material_id="construction_water",
        category="Water",
        source="Project/site allowance",
        metadata={
            "baseline_material": True,
        },
    )

    # ==================================================================
    # 6. ROOFING
    # ==================================================================

    materials.extend(
        calculate_roofing_materials(
            quantity_summary=quantity_summary,
            masonry_parameters=masonry_parameters,
        )
    )

    return materials


# ============================================================================
# COMPATIBILITY WRAPPER
# ============================================================================

def calculate_material_quantities(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
) -> List[MaterialQuantity]:
    """
    Compatibility wrapper for callers using the generic function name.
    """

    return calculate_building_materials(
        quantity_summary=quantity_summary,
        masonry_parameters=masonry_parameters,
    )


# ============================================================================
# SELF TESTS
# ============================================================================

def _run_self_tests() -> None:
    """
    Standalone Phase 10 material-calculator tests.
    """

    print("=" * 70)
    print("MATERIAL CALCULATOR TESTS")
    print("=" * 70)

    # ==================================================================
    # TEST 1: BUILDING WITHOUT ROOF
    # ==================================================================

    class TestQuantitySummary:

        total_net_wall_area_m2 = 100.0
        total_wall_volume_m3 = 20.0

        roof_present = False
        roof_area_m2 = 0.0

    quantity_summary = (
        TestQuantitySummary()
    )

    parameters = MasonryParameters(
        roof_area_m2=None,
        roof_sheet_coverage_m2=None,
        roof_timber_length_m=None,
        timber_spacing_m=None,
        water_allowance_litres=1000.0,
        quarry_stone_volume_m3=5.0,
    )

    results = calculate_building_materials(
        quantity_summary=quantity_summary,
        masonry_parameters=parameters,
    )

    material_ids = {
        item.material_id
        for item in results
    }

    # ------------------------------------------------------------------
    # Standard brick
    # ------------------------------------------------------------------

    assert (
        "standard_brick"
        in material_ids
    )

    print(
        "Standard brick: PASS"
    )

    # ------------------------------------------------------------------
    # Cement
    # ------------------------------------------------------------------

    assert (
        "cement_50kg"
        in material_ids
    )

    print(
        "Cement: PASS"
    )

    # ------------------------------------------------------------------
    # Building sand
    # ------------------------------------------------------------------

    assert (
        "building_sand"
        in material_ids
    )

    print(
        "Building sand: PASS"
    )

    # ------------------------------------------------------------------
    # Quarry stone
    # ------------------------------------------------------------------

    assert (
        "quarry_stone"
        in material_ids
    )

    print(
        "Quarry stone: PASS"
    )

    # ------------------------------------------------------------------
    # Construction water
    # ------------------------------------------------------------------

    assert (
        "construction_water"
        in material_ids
    )

    print(
        "Construction water: PASS"
    )

    # ------------------------------------------------------------------
    # Roofing must NOT appear
    # ------------------------------------------------------------------

    assert (
        "fibre_cement_sheet"
        not in material_ids
    )

    assert (
        "timber_pole_6m"
        not in material_ids
    )

    print(
        "Roofing omitted when roof is absent: PASS"
    )

    # ------------------------------------------------------------------
    # Mortar must NOT be user-facing
    # ------------------------------------------------------------------

    assert not any(
        item.material_name.lower()
        == "mortar"
        for item in results
    )

    print(
        "Mortar kept internal: PASS"
    )

    # ==================================================================
    # TEST 2: BUILDING WITH ROOF
    # ==================================================================

    class RoofQuantitySummary:

        total_net_wall_area_m2 = 100.0
        total_wall_volume_m3 = 20.0

        roof_present = True
        roof_area_m2 = 120.0

    roof_parameters = MasonryParameters(
        roof_area_m2=120.0,
        roof_sheet_coverage_m2=1.8,
        roof_timber_length_m=60.0,
        timber_spacing_m=0.6,
        water_allowance_litres=1000.0,
        quarry_stone_volume_m3=5.0,
    )

    roof_results = calculate_building_materials(
        quantity_summary=RoofQuantitySummary(),
        masonry_parameters=roof_parameters,
    )

    roof_material_ids = {
        item.material_id
        for item in roof_results
    }

    # ------------------------------------------------------------------
    # Roofing sheets
    # ------------------------------------------------------------------

    assert (
        "fibre_cement_sheet"
        in roof_material_ids
    )

    print(
        "Roofing sheets when roof is present: PASS"
    )

    # ------------------------------------------------------------------
    # Timber poles
    # ------------------------------------------------------------------

    assert (
        "timber_pole_6m"
        in roof_material_ids
    )

    print(
        "Timber poles when roof is present: PASS"
    )

    # ==================================================================
    # TEST 3: MATERIAL OBJECT VALIDATION
    # ==================================================================

    for item in results:

        assert item.quantity >= 0
        assert item.material_name
        assert item.unit

        # The returned object MUST be the current model,
        # not the temporary legacy object.
        assert isinstance(
            item,
            MaterialQuantity,
        )

    print(
        "Current MaterialQuantity conversion: PASS"
    )

    # ==================================================================
    # FINAL RESULT
    # ==================================================================

    print("-" * 70)
    print(
        "ALL MATERIAL CALCULATOR TESTS PASSED"
    )
    print("-" * 70)


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    _run_self_tests()
# ============================================================================
# STAGE-AWARE MATERIAL CALCULATION
# ============================================================================

def calculate_stage_materials(
    quantity_summary: BuildingQuantitySummary,
    masonry_parameters: MasonryParameters,
):
    """
    Calculate construction materials by construction stage.

    This function supplements calculate_building_materials().
    The original aggregate calculator remains unchanged for compatibility.

    Stages:
        1. Footing
        2. Slab
        3. Window level
        4. Final wall
        5. Roofing (only when roof information exists)

    The quantities are derived from the available architectural quantities.
    Structural assumptions used where the plan does not contain structural
    specifications are recorded in metadata.
    """

    from materials.models import StageMaterialQuantity, StageMaterialSummary

    if quantity_summary is None:
        raise ValueError("quantity_summary is required.")

    if masonry_parameters is None:
        raise ValueError("masonry_parameters is required.")

    summary = StageMaterialSummary()

    wall_length = _safe_non_negative(
        getattr(quantity_summary, "total_wall_length_m", 0.0)
    )

    wall_area = _safe_non_negative(
        getattr(quantity_summary, "total_net_wall_area_m2", 0.0)
    )

    floor_area = _safe_non_negative(
        getattr(quantity_summary, "total_floor_area_m2", 0.0)
    )

    wall_volume = _safe_non_negative(
        getattr(quantity_summary, "total_wall_volume_m3", 0.0)
    )

    wall_height = _safe_non_negative(
        getattr(masonry_parameters, "wall_height_m", 2.7)
    )

    wastage = _safe_non_negative(
        getattr(masonry_parameters, "wastage_percentage", 5.0)
    )

    # ------------------------------------------------------------------
    # Get the existing aggregate wall materials.
    # ------------------------------------------------------------------

    aggregate = calculate_building_materials(
        quantity_summary=quantity_summary,
        masonry_parameters=masonry_parameters,
    )

    aggregate_by_id = {
        getattr(item, "material_id", None): _extract_quantity(item)
        for item in aggregate
    }

    bricks_total = aggregate_by_id.get("standard_brick", 0.0)
    cement_total = aggregate_by_id.get("cement_50kg", 0.0)
    sand_total = aggregate_by_id.get("building_sand", 0.0)

    # ------------------------------------------------------------------
    # Stage 1: FOOTING
    #
    # These are estimating allowances because the architectural plan does
    # not contain structural footing reinforcement/design information.
    # ------------------------------------------------------------------

    footing_quarry_stone = _apply_wastage(
        wall_length * 0.15,
        wastage,
    )

    footing_cement = _apply_wastage(
        wall_length * 0.12,
        wastage,
    )

    footing_sand = _apply_wastage(
        wall_length * 0.025,
        wastage,
    )

    footing_water = _apply_wastage(
        wall_length * 15.0,
        wastage,
    )

    if footing_quarry_stone > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="footing",
                stage_name="Footing",
                material_id="quarry_stone",
                material_name="Quarry stone",
                quantity=_round_quantity(footing_quarry_stone),
                unit="m3",
                category="Aggregates",
                source="Wall length based footing allowance",
                metadata={
                    "wall_length_m": wall_length,
                    "allowance_m3_per_m": 0.15,
                    "estimating_allowance": True,
                },
            )
        )

    if footing_cement > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="footing",
                stage_name="Footing",
                material_id="cement_50kg",
                material_name="Cement",
                quantity=_round_quantity(footing_cement),
                unit="bag",
                category="Cement",
                source="Wall length based footing allowance",
                metadata={
                    "wall_length_m": wall_length,
                    "allowance_bags_per_m": 0.12,
                    "estimating_allowance": True,
                },
            )
        )

    if footing_sand > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="footing",
                stage_name="Footing",
                material_id="building_sand",
                material_name="Building sand",
                quantity=_round_quantity(footing_sand),
                unit="m3",
                category="Aggregates",
                source="Wall length based footing allowance",
                metadata={
                    "wall_length_m": wall_length,
                    "allowance_m3_per_m": 0.025,
                    "estimating_allowance": True,
                },
            )
        )

    if footing_water > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="footing",
                stage_name="Footing",
                material_id="construction_water",
                material_name="Construction water",
                quantity=_round_quantity(footing_water),
                unit="litres",
                category="Water",
                source="Wall length based footing allowance",
                metadata={
                    "wall_length_m": wall_length,
                    "allowance_litres_per_m": 15.0,
                    "estimating_allowance": True,
                },
            )
        )

    # ------------------------------------------------------------------
    # Stage 2: SLAB
    # ------------------------------------------------------------------

    slab_cement = _apply_wastage(
        floor_area * 0.12,
        wastage,
    )

    slab_sand = _apply_wastage(
        floor_area * 0.025,
        wastage,
    )

    slab_quarry_stone = _apply_wastage(
        floor_area * 0.06,
        wastage,
    )

    slab_hardcore = _apply_wastage(
        floor_area * 0.15,
        wastage,
    )

    slab_dpm = _apply_wastage(
        floor_area,
        wastage,
    )

    slab_water = _apply_wastage(
        floor_area * 12.0,
        wastage,
    )

    slab_materials = [
        (
            "cement_50kg",
            "Cement",
            slab_cement,
            "bag",
            "Cement",
        ),
        (
            "building_sand",
            "Building sand",
            slab_sand,
            "m3",
            "Aggregates",
        ),
        (
            "quarry_stone",
            "Quarry stone",
            slab_quarry_stone,
            "m3",
            "Aggregates",
        ),
        (
            "hardcore",
            "Hardcore",
            slab_hardcore,
            "m3",
            "Aggregates",
        ),
        (
            "dpm",
            "DPM",
            slab_dpm,
            "m2",
            "Damp proofing",
        ),
        (
            "construction_water",
            "Construction water",
            slab_water,
            "litres",
            "Water",
        ),
    ]

    for material_id, material_name, quantity, unit, category in slab_materials:
        if quantity > 0:
            summary.add(
                StageMaterialQuantity(
                    stage_id="slab",
                    stage_name="Slab",
                    material_id=material_id,
                    material_name=material_name,
                    quantity=_round_quantity(quantity),
                    unit=unit,
                    category=category,
                    source="Floor area based slab allowance",
                    metadata={
                        "floor_area_m2": floor_area,
                        "estimating_allowance": True,
                    },
                )
            )

    # ------------------------------------------------------------------
    # Stages 3 and 4: WALL CONSTRUCTION
    #
    # Split the calculated wall materials according to the wall height.
    # A 1.2 m window-level construction height is used as the estimating
    # boundary where exact sill/lintel levels are not available.
    # ------------------------------------------------------------------

    window_level_height = min(1.2, wall_height)

    if wall_height > 0:
        window_ratio = min(
            1.0,
            window_level_height / wall_height,
        )
    else:
        window_ratio = 0.0

    final_wall_ratio = max(
        0.0,
        1.0 - window_ratio,
    )

    wall_materials = [
        (
            "standard_brick",
            "Standard brick",
            bricks_total,
            "brick",
            "Masonry",
        ),
        (
            "cement_50kg",
            "Cement",
            cement_total,
            "bag",
            "Cement",
        ),
        (
            "building_sand",
            "Building sand",
            sand_total,
            "m3",
            "Aggregates",
        ),
    ]

    for material_id, material_name, total_quantity, unit, category in wall_materials:

        window_quantity = total_quantity * window_ratio
        final_quantity = total_quantity * final_wall_ratio

        if window_quantity > 0:
            summary.add(
                StageMaterialQuantity(
                    stage_id="window_level",
                    stage_name="Window level",
                    material_id=material_id,
                    material_name=material_name,
                    quantity=_round_quantity(window_quantity),
                    unit=unit,
                    category=category,
                    source="Wall quantity allocated to window level",
                    metadata={
                        "wall_height_m": wall_height,
                        "window_level_height_m": window_level_height,
                        "allocation_ratio": window_ratio,
                        "estimating_boundary": True,
                    },
                )
            )

        if final_quantity > 0:
            summary.add(
                StageMaterialQuantity(
                    stage_id="final_wall",
                    stage_name="Final wall stage",
                    material_id=material_id,
                    material_name=material_name,
                    quantity=_round_quantity(final_quantity),
                    unit=unit,
                    category=category,
                    source="Wall quantity allocated to final wall stage",
                    metadata={
                        "wall_height_m": wall_height,
                        "window_level_height_m": window_level_height,
                        "allocation_ratio": final_wall_ratio,
                        "estimating_boundary": True,
                    },
                )
            )

    # Construction water for wall stages.
    wall_water = _apply_wastage(
        wall_volume * 12.0,
        wastage,
    )

    window_water = wall_water * window_ratio
    final_water = wall_water * final_wall_ratio

    if window_water > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="window_level",
                stage_name="Window level",
                material_id="construction_water",
                material_name="Construction water",
                quantity=_round_quantity(window_water),
                unit="litres",
                category="Water",
                source="Wall volume based water allowance",
                metadata={
                    "wall_volume_m3": wall_volume,
                    "allocation_ratio": window_ratio,
                    "estimating_allowance": True,
                },
            )
        )

    if final_water > 0:
        summary.add(
            StageMaterialQuantity(
                stage_id="final_wall",
                stage_name="Final wall stage",
                material_id="construction_water",
                material_name="Construction water",
                quantity=_round_quantity(final_water),
                unit="litres",
                category="Water",
                source="Wall volume based water allowance",
                metadata={
                    "wall_volume_m3": wall_volume,
                    "allocation_ratio": final_wall_ratio,
                    "estimating_allowance": True,
                },
            )
        )

    # ------------------------------------------------------------------
    # Stage 5: ROOFING
    #
    # Never create roofing quantities unless the architectural quantity
    # summary confirms that a roof exists.
    # ------------------------------------------------------------------

    roof_present = bool(
        getattr(quantity_summary, "roof_present", False)
    )

    roof_area = _safe_non_negative(
        getattr(quantity_summary, "roof_area_m2", 0.0)
    )

    if roof_present and roof_area > 0:

        roofing_materials = calculate_roofing_materials(
            quantity_summary=quantity_summary,
            masonry_parameters=masonry_parameters,
        )

        for item in roofing_materials:
            summary.add(
                StageMaterialQuantity(
                    stage_id="roofing",
                    stage_name="Roofing",
                    material_id=getattr(item, "material_id", None),
                    material_name=item.material_name,
                    quantity=item.quantity,
                    unit=item.unit,
                    category=getattr(item, "category", None),
                    source=getattr(item, "source", "Roof calculation"),
                    metadata={
                        **(getattr(item, "metadata", {}) or {}), 
                        "roof_area_m2": roof_area,
                    },
                )
            )

    return summary
