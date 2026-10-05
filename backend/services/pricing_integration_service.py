"""
ZimBuild AI - Stage-Based Pricing Integration Service

Keeps construction stages separate during pricing.

Pipeline:

    Vision Analysis
          ↓
    Construction Parameters
          ↓
    Building Quantities
          ↓
    Stage Material Quantities
          ↓
    Stage-by-Stage Pricing
          ↓
    Stage Subtotals
          ↓
    Overall Material Subtotal
          ↓
    Transport
          ↓
    Grand Total

Roofing remains excluded.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .plan_material_quantity_service import (
    CalculatedMaterial,
    ConstructionStage,
    calculate_all_stages,
)

from .building_quantity_service import (
    calculate_building_quantities,
)

from .construction_parameters_service import (
    build_construction_parameters,
    ask_for_missing_parameters,
)

from materials.models import MaterialQuantity

from pricing.building_cost_calculator import (
    calculate_building_cost,
    BuildingCostSummary,
)


# ============================================================
# MATERIAL NAME → PRICE DATABASE ID
# ============================================================

MATERIAL_NAME_MAP = {

    # Masonry
    "Standard brick": "standard_brick",
    "Brick force": "brick_force",

    # Cement
    "Cement": "cement_50kg",
    "Cement for wall mortar": "cement_50kg",
    "Cement for slab": "cement_50kg",

    # Sand
    "Building sand": "building_sand",
    "Building sand for wall mortar": "building_sand",
    "Building sand for slab": "building_sand",

    # Stone
    "Quarry stone": "quarry_stone",
    "Quarry stone for slab": "quarry_stone",

    # Water
    "Construction water": "construction_water",

    # Openings - priced under Walls
    "Window": "window_unit",
    "Windows": "window_unit",
    "Door": "door_unit",
    "Doors": "door_unit",

    # Foundation / floor
    "Hardcore": "hardcore",
    "DPM": "dpm",
    "DPC": "dpc",

    # Structural
    "Lintel": "lintel",

    # Reinforcement
    "Reinforcement steel": "reinforcement_steel",
    "Reinforcement mesh": "reinforcement_mesh",
    "Binding wire": "binding_wire",
}


# ============================================================
# INTERMEDIATE CALCULATION MATERIALS
# ============================================================

INTERMEDIATE_MATERIALS = {
    "Wall masonry",
    "Wall mortar",
    "Slab concrete",
}


# ============================================================
# LABOUR INTEGRATION
# ============================================================

LABOUR_RATE = 0.12

DISPLAY_STAGE_ORDER = {
    1: 1,  # Foundation
    3: 2,  # Floor / Slab -> Slab
    2: 3,  # Walls
    4: 4,  # Reinforcement
}

DISPLAY_STAGE_NAMES = {
    1: "Foundation / Footing",
    2: "Slab",
    3: "Walls",
    4: "Reinforcement",
}

LABOUR_STAGE_ALLOCATION = {
    1: 0.35,
    2: 0.20,
    3: 0.30,
    4: 0.15,
}


# ============================================================
# TRANSPORT AND LOCATION COST ADJUSTMENT
# ============================================================

TRANSPORT_RATE = 0.04

LOCATION_FACTORS = {
    1: 1.20,  # City / Big Town
    2: 1.00,  # Small Town / Growth Point
    3: 0.80,  # Rural Area / Farm
}

LOCATION_NAMES = {
    1: "City / Big Town",
    2: "Small Town / Growth Point",
    3: "Rural Area / Farm",
}


# ============================================================
# PRICE-READY MATERIAL
# ============================================================

@dataclass
class PricingMaterial:

    material_id: str

    material_name: str

    quantity: float

    unit: str

    source_stage: int

    source_stage_name: str

    source_basis: str


# ============================================================
# STAGE PRICE RESULT
# ============================================================

@dataclass
class StagePricingResult:

    stage_number: int

    stage_name: str

    material_quantities: List[MaterialQuantity] = field(
        default_factory=list
    )

    cost_summary: Optional[BuildingCostSummary] = None

    skipped_materials: List[str] = field(
        default_factory=list
    )

    labour_cost: float = 0.0
    labour_percentage: float = 0.0
    transport_cost: float = 0.0
    stage_total: float = 0.0

    @property
    def subtotal(self) -> float:

        if self.cost_summary is None:
            return 0.0

        return self.cost_summary.material_subtotal


# ============================================================
# NORMALISE ONE MATERIAL
# ============================================================

def normalise_material(
    material: CalculatedMaterial,
    stage: ConstructionStage,
) -> Optional[PricingMaterial]:

    # --------------------------------------------------------
    # Intermediate calculation quantities are not purchased
    # materials, so they are skipped.
    # --------------------------------------------------------

    if material.material_name in INTERMEDIATE_MATERIALS:

        return None

    material_id = MATERIAL_NAME_MAP.get(
        material.material_name
    )

    if material_id is None:

        print(
            f"WARNING: Material not mapped for pricing: "
            f"{material.material_name}"
        )

        return None

    return PricingMaterial(

        material_id=material_id,

        material_name=material.material_name,

        quantity=float(
            material.quantity
        ),

        unit=material.unit,

        source_stage=stage.stage_number,

        source_stage_name=stage.stage_name,

        source_basis=material.basis,
    )


# ============================================================
# CONVERT ONE STAGE
# ============================================================

def convert_stage_to_pricing_materials(
    stage: ConstructionStage,
) -> List[PricingMaterial]:

    pricing_materials = []

    # Roofing is excluded.
    if stage.stage_number == 5:
        return pricing_materials

    for material in stage.materials:

        pricing_material = normalise_material(
            material=material,
            stage=stage,
        )

        if pricing_material is not None:

            pricing_materials.append(
                pricing_material
            )

    return pricing_materials


# ============================================================
# AGGREGATE WITHIN A STAGE
# ============================================================

def aggregate_stage_materials(
    materials: List[PricingMaterial],
) -> List[PricingMaterial]:

    """
    Aggregate repeated materials inside the same stage.

    Example:

        Two cement lines in one stage

    become one cement quantity for that stage.

    Materials from different stages are NOT combined.
    """

    aggregated = {}

    for material in materials:

        key = material.material_id

        if key not in aggregated:

            aggregated[key] = PricingMaterial(

                material_id=material.material_id,

                material_name=material.material_name,

                quantity=material.quantity,

                unit=material.unit,

                source_stage=material.source_stage,

                source_stage_name=(
                    material.source_stage_name
                ),

                source_basis=material.source_basis,
            )

        else:

            aggregated[key].quantity += (
                material.quantity
            )

            aggregated[key].source_basis += (
                f" | {material.source_basis}"
            )

    return list(
        aggregated.values()
    )


# ============================================================
# CONVERT TO MATERIAL QUANTITY OBJECTS
# ============================================================

def convert_to_material_quantities(
    materials: List[PricingMaterial],
) -> List[MaterialQuantity]:

    result = []

    for material in materials:

        result.append(
            MaterialQuantity(

                material_name=material.material_name,

                quantity=material.quantity,

                unit=material.unit,

                material_id=material.material_id,
            )
        )

    return result


# ============================================================
# PRINT STAGE QUANTITIES
# ============================================================

def print_stage_quantities(
    stage: ConstructionStage,
    materials: List[PricingMaterial],
):

    print()

    print("=" * 110)

    print(
        f"STAGE {stage.stage_number} - "
        f"{stage.stage_name.upper()}"
    )

    print("=" * 110)

    if not materials:

        print(
            "No priceable materials in this stage."
        )

        return

    print()

    print(
        f"{'MATERIAL':<40}"
        f"{'QUANTITY':>15}"
        f"{'UNIT':>12}"
        f"{'PRICE ID':>25}"
    )

    print("-" * 110)

    for material in materials:

        print(
            f"{material.material_name:<40}"
            f"{material.quantity:>15.3f}"
            f"{material.unit:>12}"
            f"{material.material_id:>25}"
        )

    print("-" * 110)


# ============================================================
# PRINT STAGE COST
# ============================================================

def print_stage_cost(
    result: StagePricingResult,
):

    summary = result.cost_summary

    if summary is None:
        return

    print()
    print(
        f"STAGE {result.stage_number} PRICE BREAKDOWN"
    )
    print("-" * 110)

    print(
        f"{'MATERIAL':<40}"
        f"{'QUANTITY':>15}"
        f"{'UNIT':>12}"
        f"{'UNIT PRICE':>15}"
        f"{'TOTAL':>15}"
    )

    print("-" * 110)

    for material in summary.material_costs:

        print(
            f"{material.material_name:<40}"
            f"{material.quantity:>15.3f}"
            f"{material.unit:>12}"
            f"{material.unit_price:>15.2f}"
            f"{material.material_cost:>15.2f}"
        )

    print("-" * 110)

    print(
        f"{'MATERIAL SUBTOTAL':<82}"
        f"${result.subtotal:>14,.2f}"
    )

    if result.labour_cost > 0:
        print(
            f"{'LABOUR (' + str(result.labour_percentage) + '%)':<82}"
            f"${result.labour_cost:>14,.2f}"
        )

    print(
        f"{'STAGE TOTAL':<82}"
        f"${result.stage_total:>14,.2f}"
    )

    print("-" * 110)


# ============================================================
# PRICE ONE STAGE
# ============================================================

def price_stage(
    stage: ConstructionStage,
    location_profile_id: str,
) -> StagePricingResult:

    # --------------------------------------------------------
    # Convert stage quantities.
    # --------------------------------------------------------

    pricing_materials = (
        convert_stage_to_pricing_materials(
            stage
        )
    )

    # --------------------------------------------------------
    # Aggregate ONLY within this stage.
    # --------------------------------------------------------

    pricing_materials = (
        aggregate_stage_materials(
            pricing_materials
        )
    )

    # --------------------------------------------------------
    # Convert to pricing engine objects.
    # --------------------------------------------------------

    material_quantities = (
        convert_to_material_quantities(
            pricing_materials
        )
    )

    # --------------------------------------------------------
    # Price this stage.
    #
    # Transport is deliberately zero here.
    # Transport will be added once to the overall estimate.
    # --------------------------------------------------------

    summary = calculate_building_cost(

        material_summary=material_quantities,

        location_profile_id=(
            location_profile_id
        ),

        transport_load_count=0,

        transport_distance_km=0.0,
    )

    return StagePricingResult(

        stage_number=stage.stage_number,

        stage_name=stage.stage_name,

        material_quantities=material_quantities,

        cost_summary=summary,

        labour_cost=0.0,

        labour_percentage=0.0,

        transport_cost=0.0,

        stage_total=summary.material_subtotal,
    )


# ============================================================
# PRICE ALL STAGES
# ============================================================

def price_all_stages(
    stages: List[ConstructionStage],
    location_profile_id: str = "growth_point",
) -> List[StagePricingResult]:

    results = []

    for stage in stages:

        # Roofing remains excluded.
        if stage.stage_number == 5:
            continue

        result = price_stage(
            stage=stage,
            location_profile_id=location_profile_id,
        )

        results.append(result)

    return results


def apply_labour_to_stage_results(
    stage_results: List[StagePricingResult],
) -> float:
    """Calculate project labour and allocate it to the four final stages."""

    material_subtotal = calculate_overall_material_subtotal(
        stage_results
    )

    total_labour = round(
        material_subtotal * LABOUR_RATE,
        2,
    )

    allocation_total = sum(
        LABOUR_STAGE_ALLOCATION.values()
    )

    if round(allocation_total, 10) != 1.0:
        raise ValueError(
            "Labour stage allocation must equal 100%."
        )

    for result in stage_results:

        display_stage = DISPLAY_STAGE_ORDER.get(
            result.stage_number
        )

        if display_stage is None:
            result.labour_cost = 0.0
            result.labour_percentage = 0.0
            result.stage_total = round(
                result.subtotal
                + result.labour_cost
                + result.transport_cost,
                2,
            )
            continue

        percentage = LABOUR_STAGE_ALLOCATION[
            display_stage
        ]

        result.labour_percentage = (
            percentage * 100.0
        )

        result.labour_cost = round(
            total_labour * percentage,
            2,
        )

        result.stage_total = round(
            result.subtotal
            + result.labour_cost
            + result.transport_cost,
            2,
        )

    allocated_labour = round(
        sum(
            result.labour_cost
            for result in stage_results
        ),
        2,
    )

    difference = round(
        total_labour - allocated_labour,
        2,
    )

    if abs(difference) >= 0.01:

        reinforcement = next(
            (
                result
                for result in stage_results
                if result.stage_number == 4
            ),
            None,
        )

        if reinforcement is not None:
            reinforcement.labour_cost = round(
                reinforcement.labour_cost
                + difference,
                2,
            )

            reinforcement.stage_total = round(
                reinforcement.subtotal
                + reinforcement.labour_cost
                + reinforcement.transport_cost,
                2,
            )

    return total_labour


# ============================================================
# OVERALL MATERIAL SUBTOTAL
# ============================================================

def calculate_overall_material_subtotal(
    stage_results: List[StagePricingResult],
) -> float:

    return round(
        sum(
            result.subtotal
            for result in stage_results
        ),
        2,
    )


# ============================================================
# STAGE-BASED TRANSPORT
# ============================================================

def calculate_stage_transport(
    stage_results: List[StagePricingResult],
) -> float:
    """
    Calculate transport separately for each construction stage.

    Transport is exactly 4% of the stage MATERIAL subtotal.
    Labour is deliberately excluded from this calculation.

    The four stage transport amounts are then summed to obtain
    the total project transport cost.
    """

    for result in stage_results:

        result.transport_cost = round(
            result.subtotal * TRANSPORT_RATE,
            2,
        )

        result.stage_total = round(
            result.subtotal
            + result.labour_cost
            + result.transport_cost,
            2,
        )

    total_transport = round(
        sum(
            result.transport_cost
            for result in stage_results
        ),
        2,
    )

    return total_transport


# ============================================================
# LOCATION INPUT
# ============================================================

def ask_project_location() -> tuple[int, str, float]:
    """
    Ask the user to select the project location.

    The base estimate is Small Town / Growth Point (1.00).
    City / Big Town is 1.20.
    Rural Area / Farm is 0.80.
    """

    print()
    print("=" * 70)
    print("PROJECT LOCATION")
    print("=" * 70)
    print()
    print("The location affects the overall construction cost.")
    print("The base estimate is Small Town / Growth Point.")
    print()
    print("1. City / Big Town       (×1.20)")
    print("2. Small Town / Growth Point (×1.00)")
    print("3. Rural Area / Farm     (×0.80)")
    print()

    while True:

        choice = input(
            "Select project location [1-3]: "
        ).strip()

        if choice in {"1", "2", "3"}:

            location_id = int(choice)

            return (
                location_id,
                LOCATION_NAMES[location_id],
                LOCATION_FACTORS[location_id],
            )

        print(
            "Invalid selection. Please enter 1, 2, or 3."
        )


# ============================================================
# LOCATION-ADJUSTED PROJECT TOTAL
# ============================================================

def calculate_location_adjusted_total(
    material_subtotal: float,
    labour_total: float,
    transport_total: float,
    location_factor: float,
) -> tuple[float, float]:
    """
    Calculate the base project cost and final location-adjusted cost.

    Location adjustment is applied only AFTER materials, labour and
    stage-based transport have been calculated.

        Base cost = materials + labour + transport
        Final cost = base cost × location factor
    """

    base_project_cost = round(
        material_subtotal
        + labour_total
        + transport_total,
        2,
    )

    final_project_cost = round(
        base_project_cost * location_factor,
        2,
    )

    return (
        base_project_cost,
        final_project_cost,
    )


# ============================================================
# PRINT OVERALL SUMMARY
# ============================================================

def print_overall_summary(
    stage_results: List[StagePricingResult],
    location_name: str,
    location_factor: float,
):
    """
    Print the complete project cost summary.

    Transport is already calculated per stage and stored on each
    StagePricingResult.
    """

    material_subtotal = calculate_overall_material_subtotal(
        stage_results
    )

    labour_total = round(
        sum(
            result.labour_cost
            for result in stage_results
        ),
        2,
    )

    transport_cost = round(
        sum(
            result.transport_cost
            for result in stage_results
        ),
        2,
    )

    base_project_cost, final_project_cost = (
        calculate_location_adjusted_total(
            material_subtotal=material_subtotal,
            labour_total=labour_total,
            transport_total=transport_cost,
            location_factor=location_factor,
        )
    )

    print()
    print("=" * 125)
    print("ZIMBUILD AI - OVERALL COST SUMMARY")
    print("=" * 125)
    print()

    print(
        f"{'STAGE':<40}"
        f"{'MATERIAL':>18}"
        f"{'LABOUR':>18}"
        f"{'TRANSPORT':>18}"
        f"{'STAGE TOTAL':>20}"
    )

    print("-" * 125)

    ordered_results = sorted(
        stage_results,
        key=lambda result: DISPLAY_STAGE_ORDER.get(
            result.stage_number,
            99,
        ),
    )

    for result in ordered_results:

        display_stage = DISPLAY_STAGE_ORDER.get(
            result.stage_number
        )

        stage_name = DISPLAY_STAGE_NAMES.get(
            display_stage,
            result.stage_name,
        )

        print(
            f"Stage {display_stage} - "
            f"{stage_name:<25}"
            f"${result.subtotal:>17,.2f}"
            f"${result.labour_cost:>17,.2f}"
            f"${result.transport_cost:>17,.2f}"
            f"${result.stage_total:>19,.2f}"
        )

    print("-" * 125)

    print(
        f"{'MATERIAL SUBTOTAL':<95}"
        f"${material_subtotal:>29,.2f}"
    )

    print(
        f"{'TOTAL LABOUR (12%)':<95}"
        f"${labour_total:>29,.2f}"
    )

    print(
        f"{'TOTAL TRANSPORT (4% OF STAGE MATERIALS)':<95}"
        f"${transport_cost:>29,.2f}"
    )

    print(
        f"{'BASE PROJECT COST BEFORE LOCATION ADJUSTMENT':<95}"
        f"${base_project_cost:>29,.2f}"
    )

    print()
    print(
        f"{'PROJECT LOCATION':<70}"
        f"{location_name}"
    )

    print(
        f"{'LOCATION FACTOR':<70}"
        f"×{location_factor:.2f}"
    )

    print("=" * 125)

    print(
        f"{'FINAL ESTIMATED PROJECT COST':<95}"
        f"${final_project_cost:>29,.2f}"
    )

    print("=" * 125)
    print()
    print("Currency: USD")


# ============================================================
# COMPLETE STAGE-BASED PRICING PIPELINE
# ============================================================

def calculate_complete_stage_pricing():
    """
    Run the complete quantity, pricing, labour, transport and
    location-adjusted cost pipeline.
    """

    print()
    print("=" * 110)
    print(
        "ZIMBUILD AI - STAGE-BASED QUANTITY → PRICING PIPELINE"
    )
    print("=" * 110)

    # ========================================================
    # STEP 1 - CONSTRUCTION PARAMETERS
    # ========================================================

    print()
    print("STEP 1 - CONSTRUCTION PARAMETERS")
    print("-" * 110)

    parameters = build_construction_parameters()

    parameters = ask_for_missing_parameters(
        parameters
    )

    location_id, location_name, location_factor = (
        ask_project_location()
    )

    # ========================================================
    # STEP 2 - BUILDING QUANTITIES
    # ========================================================

    print()
    print("STEP 2 - BUILDING QUANTITIES")
    print("-" * 110)

    building = calculate_building_quantities(
        parameters
    )

    # ========================================================
    # STEP 3 - MATERIAL QUANTITIES
    # ========================================================

    print()
    print("STEP 3 - MATERIAL QUANTITIES")
    print("-" * 110)

    stages = calculate_all_stages(
        building,
        parameters,
    )

    # Windows and doors are priced under Walls.
    for stage in stages:

        if stage.stage_number != 2:
            continue

        window_count = int(
            getattr(
                building,
                "window_count",
                0,
            ) or 0
        )

        door_count = int(
            getattr(
                building,
                "door_count",
                0,
            ) or 0
        )

        if window_count > 0:
            stage.materials.append(
                CalculatedMaterial(
                    material_name="Windows",
                    quantity=float(window_count),
                    unit="unit",
                    basis="Vision-detected window count",
                )
            )

        if door_count > 0:
            stage.materials.append(
                CalculatedMaterial(
                    material_name="Doors",
                    quantity=float(door_count),
                    unit="unit",
                    basis="Vision-detected door count",
                )
            )

        break

    # ========================================================
    # STEP 4 - STAGE-BY-STAGE PRICING
    # ========================================================

    print()
    print("STEP 4 - STAGE-BY-STAGE PRICING")
    print("-" * 110)

    stage_results = price_all_stages(
        stages=stages,
        location_profile_id="growth_point",
    )

    # ========================================================
    # STEP 5 - LABOUR
    # ========================================================

    print()
    print("STEP 5 - LABOUR")
    print("-" * 110)

    labour_total = apply_labour_to_stage_results(
        stage_results
    )

    material_subtotal = calculate_overall_material_subtotal(
        stage_results
    )

    print(
        f"Total material subtotal before labour: "
        f"${material_subtotal:,.2f}"
    )

    print(
        f"Labour rate: {LABOUR_RATE * 100:.0f}%"
    )

    print(
        f"Total labour: ${labour_total:,.2f}"
    )

    print(
        "Labour allocation: "
        "Foundation 35% | Slab 20% | Walls 30% | "
        "Reinforcement 15%"
    )

    # ========================================================
    # STEP 6 - STAGE-BASED TRANSPORT
    # ========================================================

    print()
    print("STEP 6 - STAGE-BASED TRANSPORT")
    print("-" * 110)

    transport_total = calculate_stage_transport(
        stage_results
    )

    print()
    print(
        "Transport is calculated as 4% of each stage's "
        "MATERIAL subtotal only."
    )

    ordered_results = sorted(
        stage_results,
        key=lambda result: DISPLAY_STAGE_ORDER.get(
            result.stage_number,
            99,
        ),
    )

    for result in ordered_results:

        display_stage = DISPLAY_STAGE_ORDER.get(
            result.stage_number
        )

        stage_name = DISPLAY_STAGE_NAMES.get(
            display_stage,
            result.stage_name,
        )

        print(
            f"Stage {display_stage} - "
            f"{stage_name:<25}"
            f"Materials: ${result.subtotal:>12,.2f} | "
            f"Transport (4%): ${result.transport_cost:>10,.2f}"
        )

    print(
        f"Total project transport: ${transport_total:,.2f}"
    )

    # ========================================================
    # DISPLAY EACH STAGE
    # ========================================================

    stage_lookup = {
        stage.stage_number: stage
        for stage in stages
    }

    for result in ordered_results:

        stage = stage_lookup.get(
            result.stage_number
        )

        if stage is None:
            continue

        print_stage_quantities(
            stage,
            [
                PricingMaterial(
                    material_id=material.material_id,
                    material_name=material.material_name,
                    quantity=material.quantity,
                    unit=material.unit,
                    source_stage=stage.stage_number,
                    source_stage_name=stage.stage_name,
                    source_basis="",
                )
                for material in result.material_quantities
            ],
        )

        print_stage_cost(
            result
        )

        print(
            f"{'TRANSPORT (4% OF MATERIALS)':<82}"
            f"${result.transport_cost:>14,.2f}"
        )

        print(
            f"{'STAGE TOTAL INCLUDING LABOUR + TRANSPORT':<82}"
            f"${result.stage_total:>14,.2f}"
        )

    # ========================================================
    # STEP 7 - FINAL PROJECT TOTAL WITH LOCATION
    # ========================================================

    print()
    print("STEP 7 - LOCATION ADJUSTMENT & FINAL PROJECT TOTAL")
    print("-" * 110)

    base_project_cost, final_project_cost = (
        calculate_location_adjusted_total(
            material_subtotal=material_subtotal,
            labour_total=labour_total,
            transport_total=transport_total,
            location_factor=location_factor,
        )
    )

    print(
        f"Selected location: {location_name}"
    )

    print(
        f"Location factor: ×{location_factor:.2f}"
    )

    print(
        f"Base project cost before location adjustment: "
        f"${base_project_cost:,.2f}"
    )

    print(
        f"Final estimated project cost: "
        f"${final_project_cost:,.2f}"
    )

    print_overall_summary(
        stage_results=stage_results,
        location_name=location_name,
        location_factor=location_factor,
    )

    return (
        parameters,
        building,
        stages,
        stage_results,
        transport_total,
        location_id,
        location_name,
        location_factor,
        base_project_cost,
        final_project_cost,
    )


# ============================================================
# SELF TESTS
# ============================================================

def run_self_tests():

    print()

    print("=" * 90)

    print(
        "STAGE-BASED PRICING INTEGRATION TESTS"
    )

    print("=" * 90)

    # --------------------------------------------------------
    # Test material mapping
    # --------------------------------------------------------

    cement = CalculatedMaterial(

        material_name="Cement for wall mortar",

        quantity=100,

        unit="bag",

        basis="Wall mortar",
    )

    stage = ConstructionStage(

        stage_number=2,

        stage_name="Walls",

        materials=[cement],
    )

    result = normalise_material(
        cement,
        stage,
    )

    assert result is not None

    assert (
        result.material_id
        == "cement_50kg"
    )

    print(
        "Stage material normalisation: PASS"
    )

    # --------------------------------------------------------
    # Test intermediate materials
    # --------------------------------------------------------

    wall_masonry = CalculatedMaterial(

        material_name="Wall masonry",

        quantity=60.323,

        unit="m3",

        basis="Wall calculation",
    )

    result = normalise_material(
        wall_masonry,
        stage,
    )

    assert result is None

    print(
        "Intermediate material exclusion: PASS"
    )

    # --------------------------------------------------------
    # Test stage pricing
    # --------------------------------------------------------

    test_stage = ConstructionStage(

        stage_number=1,

        stage_name="Foundation",

        materials=[

            CalculatedMaterial(
                material_name="Cement",
                quantity=10,
                unit="bag",
                basis="Foundation",
            ),

            CalculatedMaterial(
                material_name="Building sand",
                quantity=2,
                unit="m3",
                basis="Foundation",
            ),

            CalculatedMaterial(
                material_name="Quarry stone",
                quantity=3,
                unit="m3",
                basis="Foundation",
            ),
        ],
    )

    priced_stage = price_stage(

        stage=test_stage,

        location_profile_id="growth_point",
    )

    assert (
        priced_stage.cost_summary
        is not None
    )

    assert (
        priced_stage.subtotal
        > 0
    )

    print(
        "Stage pricing: PASS"
    )

    # --------------------------------------------------------
    # Test stage separation
    # --------------------------------------------------------

    stage_one = ConstructionStage(

        stage_number=1,

        stage_name="Foundation",

        materials=[

            CalculatedMaterial(
                material_name="Cement",
                quantity=10,
                unit="bag",
                basis="Foundation",
            )
        ],
    )

    stage_two = ConstructionStage(

        stage_number=2,

        stage_name="Walls",

        materials=[

            CalculatedMaterial(
                material_name="Cement",
                quantity=20,
                unit="bag",
                basis="Walls",
            )
        ],
    )

    results = price_all_stages(

        stages=[
            stage_one,
            stage_two,
        ],

        location_profile_id="growth_point",
    )

    assert (
        len(results)
        == 2
    )

    assert (
        results[0].stage_number
        == 1
    )

    assert (
        results[1].stage_number
        == 2
    )

    assert (
        results[0].cost_summary
        is not None
    )

    assert (
        results[1].cost_summary
        is not None
    )

    print(
        "Stage separation: PASS"
    )

    # --------------------------------------------------------
    # Test overall subtotal
    # --------------------------------------------------------

    subtotal = (
        calculate_overall_material_subtotal(
            results
        )
    )

    assert subtotal > 0

    print(
        "Overall subtotal calculation: PASS"
    )

    # --------------------------------------------------------
    # --------------------------------------------------------
    # Test 12% labour
    #
    # Labour allocation is a four-stage project rule, so this
    # test uses all four construction stages.
    # --------------------------------------------------------

    labour_test_stages = [
        ConstructionStage(
            stage_number=1,
            stage_name="Foundation",
            materials=[
                CalculatedMaterial(
                    material_name="Cement",
                    quantity=10,
                    unit="bag",
                    basis="Foundation",
                )
            ],
        ),
        ConstructionStage(
            stage_number=2,
            stage_name="Walls",
            materials=[
                CalculatedMaterial(
                    material_name="Cement",
                    quantity=20,
                    unit="bag",
                    basis="Walls",
                )
            ],
        ),
        ConstructionStage(
            stage_number=3,
            stage_name="Floor / Slab",
            materials=[
                CalculatedMaterial(
                    material_name="Cement",
                    quantity=15,
                    unit="bag",
                    basis="Slab",
                )
            ],
        ),
        ConstructionStage(
            stage_number=4,
            stage_name="Reinforcement",
            materials=[
                CalculatedMaterial(
                    material_name="Reinforcement steel",
                    quantity=100,
                    unit="m",
                    basis="Reinforcement",
                )
            ],
        ),
    ]

    labour_results = price_all_stages(
        stages=labour_test_stages,
        location_profile_id="growth_point",
    )

    labour_subtotal = (
        calculate_overall_material_subtotal(
            labour_results
        )
    )

    labour_total = apply_labour_to_stage_results(
        labour_results
    )

    expected_labour = round(
        labour_subtotal * LABOUR_RATE,
        2,
    )

    assert labour_total == expected_labour

    assert (
        round(
            sum(
                result.labour_cost
                for result in labour_results
            ),
            2,
        )
        == expected_labour
    )

    print(
        "12% total labour calculation: PASS"
    )

    # --------------------------------------------------------
    # Test labour allocation
    # --------------------------------------------------------

    expected_allocations = {
        1: 35.0,
        2: 20.0,
        3: 30.0,
        4: 15.0,
    }

    assert (
        round(
            sum(
                result.labour_percentage
                for result in labour_results
            ),
            2,
        )
        == 100.0
    )

    for result in labour_results:

        display_stage = DISPLAY_STAGE_ORDER[
            result.stage_number
        ]

        assert (
            result.labour_percentage
            == expected_allocations[
                display_stage
            ]
        )

    print(
        "Labour stage allocation: PASS"
    )

    # --------------------------------------------------------
    # Test stage totals
    # --------------------------------------------------------

    for result in labour_results:

        assert (
            round(
                result.stage_total,
                2,
            )
            == round(
                result.subtotal
                + result.labour_cost,
                2,
            )
        )

    print(
        "Stage total after labour: PASS"
    )

    # --------------------------------------------------------
    # Test 4% stage transport
    # --------------------------------------------------------

    transport_test_results = labour_results

    transport_total = calculate_stage_transport(
        transport_test_results
    )

    expected_transport = round(
        sum(
            result.subtotal * TRANSPORT_RATE
            for result in transport_test_results
        ),
        2,
    )

    assert transport_total == expected_transport

    for result in transport_test_results:

        assert (
            result.transport_cost
            == round(
                result.subtotal * TRANSPORT_RATE,
                2,
            )
        )

        assert (
            round(
                result.stage_total,
                2,
            )
            == round(
                result.subtotal
                + result.labour_cost
                + result.transport_cost,
                2,
            )
        )

    print(
        "4% stage transport calculation: PASS"
    )

    # --------------------------------------------------------
    # Test location factors
    # --------------------------------------------------------

    assert LOCATION_FACTORS[1] == 1.20
    assert LOCATION_FACTORS[2] == 1.00
    assert LOCATION_FACTORS[3] == 0.80

    test_materials = 1000.00
    test_labour = 120.00
    test_transport = 40.00

    base_cost, city_cost = calculate_location_adjusted_total(
        material_subtotal=test_materials,
        labour_total=test_labour,
        transport_total=test_transport,
        location_factor=LOCATION_FACTORS[1],
    )

    assert base_cost == 1160.00
    assert city_cost == 1392.00

    _, growth_point_cost = calculate_location_adjusted_total(
        material_subtotal=test_materials,
        labour_total=test_labour,
        transport_total=test_transport,
        location_factor=LOCATION_FACTORS[2],
    )

    _, rural_cost = calculate_location_adjusted_total(
        material_subtotal=test_materials,
        labour_total=test_labour,
        transport_total=test_transport,
        location_factor=LOCATION_FACTORS[3],
    )

    assert growth_point_cost == 1160.00
    assert rural_cost == 928.00

    print(
        "Location cost adjustment calculation: PASS"
    )

    # --------------------------------------------------------
    # Test final calculation order
    # --------------------------------------------------------

    # Location must be applied AFTER materials, labour and transport.
    expected_final = round(
        (test_materials + test_labour + test_transport)
        * 1.20,
        2,
    )

    assert city_cost == expected_final

    print(
        "Final calculation order: PASS"
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print()

    print(
        "ALL STAGE-BASED PRICING TESTS PASSED"
    )

    print("=" * 90)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    import sys

    run_self_tests()

    if "--full" in sys.argv:

        print()
        print("=" * 90)
        print("SELF-TESTS PASSED - STARTING FULL PIPELINE")
        print("=" * 90)

        calculate_complete_stage_pricing()
