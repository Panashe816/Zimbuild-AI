"""

ZimBuild AI - Pricing Integration Service



Purpose:

    Connect the construction quantity calculation system to the

    pricing and building cost calculation system.



Pipeline:

    Vision Analysis

        â†“

    Construction Parameters

        â†“

    Building Quantities

        â†“

    Stage Material Quantities

        â†“

    Material Pricing

        â†“

    Labour

        â†“

    Transport

        â†“

    Stage Totals

        â†“

    Overall Building Cost



Construction stages:

    1. Foundation / Footing

    2. Slab

    3. Walls

    4. Reinforcement



Roofing is intentionally excluded.

"""



from __future__ import annotations



from dataclasses import dataclass, field

from typing import Any, Dict, List, Optional



from backend.services.building_quantity_service import (

    calculate_building_quantities,

)



from backend.services.construction_parameters_service import (

    build_construction_parameters,

    ask_for_missing_parameters,

)



from .building_cost_calculator import (

    BuildingCostSummary,

    calculate_building_cost,

)



from .price_database import (

    DEFAULT_TRANSPORT_RATE,

    get_transport_rate,

)



@dataclass

class MaterialQuantity:

    """Material quantity passed to the building cost calculator."""



    material_id: str

    quantity: float

    unit: str





# ============================================================

# CONFIGURATION

# ============================================================



LABOUR_RATE = 0.12



DEFAULT_DISTANCE_KM = 10.0



# Construction stage mapping

#

# User-facing stage order:

#

# 1 = Foundation

# 2 = Slab

# 3 = Walls

# 4 = Reinforcement

#

# Internal material quantity engine currently uses:

# 1 = Foundation

# 2 = Walls

# 3 = Floor / Slab

# 4 = Reinforcement

#

# Therefore:

# User stage 1 -> internal stage 1

# User stage 2 -> internal stage 3

# User stage 3 -> internal stage 2

# User stage 4 -> internal stage 4



USER_STAGE_TO_INTERNAL_STAGE = {

    1: 1,

    2: 3,

    3: 2,

    4: 4,

}





STAGE_NAMES = {

    1: "Foundation / Footing",

    2: "Slab",

    3: "Walls",

    4: "Reinforcement",

}





# ============================================================

# MATERIAL NAME MAPPING

# ============================================================



MATERIAL_NAME_MAP = {

    "standard brick": "standard_brick",

    "brick": "standard_brick",



    "brick force": "brick_force",



    "cement": "cement_50kg",

    "cement 50kg": "cement_50kg",



    "building sand": "building_sand",

    "sand": "building_sand",



    "quarry stone": "quarry_stone",

    "stone": "quarry_stone",



    "quarry dust": "quarry_dust",



    "construction water": "construction_water",

    "water": "construction_water",



    "reinforcement steel": "reinforcement_steel",

    "steel reinforcement": "reinforcement_steel",

    "steel": "reinforcement_steel",



    "reinforcement mesh": "reinforcement_mesh",

    "mesh": "reinforcement_mesh",



    "binding wire": "binding_wire",



    "hardcore": "hardcore",



    "damp-proof membrane": "dpm",

    "dpm": "dpm",



    "damp-proof course": "dpc",

    "dpc": "dpc",



    "lintel": "lintel",



    "window": "window_unit",

    "windows": "window_unit",



    "door": "door_unit",

    "doors": "door_unit",



    "formwork timber": "formwork_timber",

    "formwork": "formwork_timber",



    "nails": "nails",



    "fibre cement sheet": "fibre_cement_sheet",

    "fibre-cement sheet": "fibre_cement_sheet",



    "timber pole 6m": "timber_pole_6m",

    "timber pole": "timber_pole_6m",



    "roofing timber": "roofing_timber",



    "ridge cap": "ridge_cap",



    "fascia": "fascia",

}





# ============================================================

# INTERMEDIATE MATERIALS

# ============================================================



# These are calculation intermediates and must not be priced

# directly as purchased materials.



INTERMEDIATE_MATERIALS = {

    "wall masonry",

    "wall mortar",

    "foundation concrete",

    "slab concrete",

}





# ============================================================

# DATA CLASSES

# ============================================================



@dataclass

class PricingMaterial:

    """

    Material ready to be sent into the pricing engine.

    """



    name: str

    quantity: float

    unit: str

    material_id: Optional[str] = None





@dataclass

class StagePricingResult:

    """

    Pricing result for one construction stage.

    """



    stage_number: int

    stage_name: str



    materials: List[Dict[str, Any]] = field(default_factory=list)



    material_subtotal: float = 0.0

    labour_cost: float = 0.0

    transport_cost: float = 0.0



    stage_total: float = 0.0





@dataclass

class CompletePricingResult:

    """

    Complete building pricing result.

    """



    stages: List[StagePricingResult] = field(default_factory=list)



    materials_total: float = 0.0

    labour_total: float = 0.0

    transport_total: float = 0.0



    grand_total: float = 0.0





# ============================================================

# MATERIAL NAME NORMALISATION

# ============================================================



def normalise_material_name(name: str) -> str:

    """

    Convert material names into a consistent lowercase format.

    """



    if not name:

        return ""



    return (

        name

        .strip()

        .lower()

        .replace("_", " ")

        .replace("-", " ")

    )





def resolve_material_id(

    material_name: str,

    explicit_material_id: Optional[str] = None,

) -> Optional[str]:

    """

    Resolve the pricing database material ID.

    """



    if explicit_material_id:

        return explicit_material_id



    normalised = normalise_material_name(material_name)



    return MATERIAL_NAME_MAP.get(normalised)





# ============================================================

# STAGE MATERIAL CONVERSION

# ============================================================



def convert_stage_to_pricing_materials(

    materials: List[Any],

) -> List[PricingMaterial]:

    """

    Convert calculated material objects into pricing materials.



    Intermediate calculation materials such as Wall masonry and

    Wall mortar are excluded from pricing.

    """



    pricing_materials: List[PricingMaterial] = []



    for material in materials:



        name = getattr(material, "name", "")

        quantity = float(getattr(material, "quantity", 0.0))

        unit = getattr(material, "unit", "")



        if not name:

            continue



        normalised_name = normalise_material_name(name)



        if normalised_name in INTERMEDIATE_MATERIALS:

            continue



        material_id = resolve_material_id(

            name,

            getattr(material, "material_id", None),

        )



        pricing_materials.append(

            PricingMaterial(

                name=name,

                quantity=quantity,

                unit=unit,

                material_id=material_id,

            )

        )



    return pricing_materials





# ============================================================

# MATERIAL QUANTITY CONVERSION

# ============================================================



def convert_to_material_quantities(

    materials: List[PricingMaterial],

) -> List[MaterialQuantity]:

    """

    Convert pricing materials into the format expected by

    BuildingCostCalculator.

    """



    converted: List[MaterialQuantity] = []



    for material in materials:



        material_id = material.material_id



        if not material_id:

            material_id = resolve_material_id(material.name)



        if not material_id:

            continue



        converted.append(

            MaterialQuantity(

                material_id=material_id,

                quantity=float(material.quantity),

                unit=material.unit,

            )

        )



    return converted





# ============================================================

# OPENING MATERIALS

# ============================================================



def add_opening_materials(

    material_list: List[PricingMaterial],

    building: Any,

) -> List[PricingMaterial]:

    """

    Add fixed-price windows and doors to the Walls stage.



    Windows:

        $30 each



    Doors:

        $50 each

    """



    result = list(material_list)



    window_count = int(

        getattr(building, "window_count", 0) or 0

    )



    door_count = int(

        getattr(building, "door_count", 0) or 0

    )



    if window_count > 0:

        result.append(

            PricingMaterial(

                name="Window",

                quantity=float(window_count),

                unit="each",

                material_id="window_unit",

            )

        )



    if door_count > 0:

        result.append(

            PricingMaterial(

                name="Door",

                quantity=float(door_count),

                unit="each",

                material_id="door_unit",

            )

        )



    return result





# ============================================================

# STAGE PRICING

# ============================================================



def price_stage(

    stage_number: int,

    materials: List[PricingMaterial],

    location_profile: str = DEFAULT_TRANSPORT_RATE,

    distance_km: float = DEFAULT_DISTANCE_KM,

) -> StagePricingResult:

    """

    Price one construction stage.



    Labour:

        12% of material subtotal.



    Transport:

        Calculated from material load value and location profile.

    """



    stage_name = STAGE_NAMES[stage_number]



    material_quantities = convert_to_material_quantities(

        materials

    )



    if not material_quantities:

        return StagePricingResult(

            stage_number=stage_number,

            stage_name=stage_name,

            materials=[],

            material_subtotal=0.0,

            labour_cost=0.0,

            transport_cost=0.0,

            stage_total=0.0,

        )



    # BuildingCostCalculator expects the complete material summary

    # as its first argument, not a keyword called material_quantities.

    #

    # First calculate the material subtotal with no transport, then

    # calculate the required number of loads and run the calculator

    # again so transport is included correctly.

    base_summary: BuildingCostSummary = calculate_building_cost(

        material_quantities,

        location_profile_id=location_profile,

        transport_load_count=0,

        transport_distance_km=distance_km,

    )



    material_subtotal = float(

        base_summary.material_subtotal

    )



    transport_loads = max(

        1,

        int((material_subtotal + 999.99) // 1000),

    )



    cost_summary: BuildingCostSummary = calculate_building_cost(

        material_quantities,

        location_profile_id=location_profile,

        transport_load_count=transport_loads,

        transport_distance_km=distance_km,

    )



    material_details: List[Dict[str, Any]] = []



    for material_cost in cost_summary.material_costs:



        material_details.append(

            {

                "material_id": resolve_material_id(material_cost.material_name),

                "material_name": material_cost.material_name,

                "quantity": material_cost.quantity,

                "unit": material_cost.unit,

                "unit_price": material_cost.unit_price,

                "total_cost": material_cost.material_cost,

            }

        )



    material_subtotal = float(

        cost_summary.material_subtotal

    )



    labour_cost = material_subtotal * LABOUR_RATE



    transport_cost = float(

        cost_summary.transport_cost

    )



    stage_total = (

        material_subtotal

        + labour_cost

        + transport_cost

    )



    return StagePricingResult(

        stage_number=stage_number,

        stage_name=stage_name,

        materials=material_details,

        material_subtotal=material_subtotal,

        labour_cost=labour_cost,

        transport_cost=transport_cost,

        stage_total=stage_total,

    )





# ============================================================

# PRICE ALL STAGES

# ============================================================



def price_all_stages(

    stage_materials: Dict[int, List[Any]],

    building: Any,

    location_profile: str = DEFAULT_TRANSPORT_RATE,

    distance_km: float = DEFAULT_DISTANCE_KM,

) -> CompletePricingResult:

    """

    Price all four construction stages.



    User-facing order:

        1. Foundation

        2. Slab

        3. Walls

        4. Reinforcement

    """



    results: List[StagePricingResult] = []



    for user_stage in range(1, 5):



        internal_stage = USER_STAGE_TO_INTERNAL_STAGE[

            user_stage

        ]



        raw_materials = stage_materials.get(

            internal_stage,

            [],

        )



        pricing_materials = (

            convert_stage_to_pricing_materials(

                raw_materials

            )

        )



        # Windows and doors belong to Walls.

        if user_stage == 3:

            pricing_materials = add_opening_materials(

                pricing_materials,

                building,

            )



        stage_result = price_stage(

            stage_number=user_stage,

            materials=pricing_materials,

            location_profile=location_profile,

            distance_km=distance_km,

        )



        results.append(stage_result)



    return calculate_overall_totals(results)





# ============================================================

# TRANSPORT

# ============================================================



def calculate_transport_cost(

    material_subtotal: float,

    location_profile: str = DEFAULT_TRANSPORT_RATE,

    distance_km: float = DEFAULT_DISTANCE_KM,

) -> float:

    """

    Calculate transport cost.



    Transport is based on:

        material subtotal Ã— transport rate Ã— distance factor

    """



    rate = get_transport_rate(location_profile)



    if distance_km < 0:

        raise ValueError(

            "Distance cannot be negative."

        )



    # One transport load is assumed for each $1,000

    # worth of materials, rounded up.



    loads = max(

        1,

        int((material_subtotal + 999.99) // 1000),

    )



    return (

        loads

        * rate.price_per_load_per_km

        * distance_km

    )





# ============================================================

# APPLY STAGE TRANSPORT

# ============================================================



def apply_stage_transport(

    stage_result: StagePricingResult,

    location_profile: str = DEFAULT_TRANSPORT_RATE,

    distance_km: float = DEFAULT_DISTANCE_KM,

) -> StagePricingResult:

    """

    Apply transport to an already calculated stage.



    This function is retained for compatibility.

    """



    transport_cost = calculate_transport_cost(

        material_subtotal=stage_result.material_subtotal,

        location_profile=location_profile,

        distance_km=distance_km,

    )



    stage_result.transport_cost = transport_cost



    stage_result.stage_total = (

        stage_result.material_subtotal

        + stage_result.labour_cost

        + stage_result.transport_cost

    )



    return stage_result





# ============================================================

# OVERALL TOTALS

# ============================================================



def calculate_overall_totals(

    stages: List[StagePricingResult],

) -> CompletePricingResult:

    """

    Calculate building-wide totals.

    """



    materials_total = sum(

        stage.material_subtotal

        for stage in stages

    )



    labour_total = sum(

        stage.labour_cost

        for stage in stages

    )



    transport_total = sum(

        stage.transport_cost

        for stage in stages

    )



    grand_total = (

        materials_total

        + labour_total

        + transport_total

    )



    return CompletePricingResult(

        stages=stages,

        materials_total=materials_total,

        labour_total=labour_total,

        transport_total=transport_total,

        grand_total=grand_total,

    )





# ============================================================

# DISPLAY HELPERS

# ============================================================



def print_stage_materials(

    stage: StagePricingResult,

) -> None:

    """

    Print materials belonging to a stage.

    """



    print()

    print("=" * 72)

    print(

        f"STAGE {stage.stage_number}: "

        f"{stage.stage_name.upper()}"

    )

    print("=" * 72)



    if not stage.materials:

        print("No priced materials.")



    else:



        for material in stage.materials:



            quantity = material["quantity"]

            unit = material["unit"]

            unit_price = material["unit_price"]

            total_cost = material["total_cost"]



            print(

                f"{material['material_name']}: "

                f"{quantity:.2f} {unit} Ã— "

                f"${unit_price:.2f} = "

                f"${total_cost:.2f}"

            )



    print()

    print(

        f"Materials subtotal: "

        f"${stage.material_subtotal:,.2f}"

    )



    print(

        f"Labour (12%): "

        f"${stage.labour_cost:,.2f}"

    )



    print(

        f"Transport: "

        f"${stage.transport_cost:,.2f}"

    )



    print(

        f"STAGE TOTAL: "

        f"${stage.stage_total:,.2f}"

    )





def print_stage_result(

    stage: StagePricingResult,

) -> None:

    """

    Print a complete stage result.

    """



    print_stage_materials(stage)





def print_complete_result(

    result: CompletePricingResult,

) -> None:

    """

    Print complete building pricing report.

    """



    print()

    print("#" * 72)

    print("ZIMBUILD AI - COMPLETE BUILDING COST ESTIMATE")

    print("#" * 72)



    for stage in result.stages:

        print_stage_result(stage)



    print()

    print("#" * 72)

    print("OVERALL COST SUMMARY")

    print("#" * 72)



    print(

        f"Materials Total: "

        f"${result.materials_total:,.2f}"

    )



    print(

        f"Labour Total: "

        f"${result.labour_total:,.2f}"

    )



    print(

        f"Transport Total: "

        f"${result.transport_total:,.2f}"

    )



    print("-" * 72)



    print(

        f"GRAND TOTAL: "

        f"${result.grand_total:,.2f}"

    )



    print("#" * 72)





# ============================================================

# COMPLETE PRICING PIPELINE

# ============================================================



def calculate_complete_stage_pricing(

    location_profile: str = DEFAULT_TRANSPORT_RATE,

    distance_km: float = DEFAULT_DISTANCE_KM,

) -> CompletePricingResult:

    """

    Run the complete quantity-to-price pipeline.



    Workflow:



        Vision analysis

            â†“

        Construction parameters

            â†“

        Building quantities

            â†“

        Material quantities

            â†“

        Pricing

            â†“

        Labour

            â†“

        Transport

            â†“

        Final cost

    """



    print()

    print("=" * 72)

    print("ZIMBUILD AI - PRICING INTEGRATION")

    print("=" * 72)



    print()

    print("Collecting construction parameters...")



    parameters = build_construction_parameters()

    parameters = ask_for_missing_parameters(parameters)



    print()

    print("Calculating building quantities...")



    building = calculate_building_quantities(

        parameters

    )



    print()

    print("Calculating construction material quantities...")



    # Import locally to avoid circular imports.

    from backend.services.plan_material_quantity_service import (

        calculate_complete_material_quantities,

    )



    material_result = calculate_complete_material_quantities(

        parameters

    )



    # Extract stages.

    stage_materials: Dict[int, List[Any]] = {}



    for stage in material_result.stages:



        stage_materials[

            stage.stage_number

        ] = stage.materials



    print()

    print("Calculating material prices...")



    result = price_all_stages(

        stage_materials=stage_materials,

        building=building,

        location_profile=location_profile,

        distance_km=distance_km,

    )



    return result





# ============================================================

# SELF TESTS

# ============================================================



def run_self_tests() -> None:

    """

    Run basic integration tests without requiring user input.

    """



    print()

    print("=" * 72)

    print("PRICING INTEGRATION SERVICE TESTS")

    print("=" * 72)



    # --------------------------------------------------------

    # Test material name normalisation

    # --------------------------------------------------------



    assert (

        normalise_material_name("Standard Brick")

        == "standard brick"

    )



    assert (

        normalise_material_name("Brick-Force")

        == "brick force"

    )



    print("Material name normalisation: PASS")



    # --------------------------------------------------------

    # Test material ID resolution

    # --------------------------------------------------------



    assert (

        resolve_material_id("Standard Brick")

        == "standard_brick"

    )



    assert (

        resolve_material_id("Cement")

        == "cement_50kg"

    )



    assert (

        resolve_material_id("Building Sand")

        == "building_sand"

    )



    print("Material ID resolution: PASS")



    # --------------------------------------------------------

    # Test intermediate material filtering

    # --------------------------------------------------------



    sample_materials = [

        PricingMaterial(

            name="Wall masonry",

            quantity=10,

            unit="m3",

        ),

        PricingMaterial(

            name="Cement",

            quantity=10,

            unit="bag",

            material_id="cement_50kg",

        ),

        PricingMaterial(

            name="Building sand",

            quantity=5,

            unit="m3",

            material_id="building_sand",

        ),

    ]



    converted = convert_stage_to_pricing_materials(

        sample_materials

    )



    assert len(converted) == 2



    print("Intermediate material filtering: PASS")



    # --------------------------------------------------------

    # Test opening materials

    # --------------------------------------------------------



    class TestBuilding:

        window_count = 11

        door_count = 8



    openings = add_opening_materials(

        [],

        TestBuilding(),

    )



    assert len(openings) == 2



    assert (

        openings[0].material_id

        == "window_unit"

    )



    assert (

        openings[1].material_id

        == "door_unit"

    )



    assert openings[0].quantity == 11

    assert openings[1].quantity == 8



    print("Window and door integration: PASS")



    # --------------------------------------------------------

    # Test stage pricing

    # --------------------------------------------------------



    test_stage_materials = [

        PricingMaterial(

            name="Standard brick",

            quantity=1000,

            unit="brick",

            material_id="standard_brick",

        ),

    ]



    stage = price_stage(

        stage_number=3,

        materials=test_stage_materials,

        location_profile="growth_point",

        distance_km=0,

    )



    assert stage.material_subtotal > 0



    assert (

        abs(

            stage.labour_cost

            - stage.material_subtotal * LABOUR_RATE

        )

        < 0.000001

    )



    assert (

        abs(

            stage.stage_total

            - (

                stage.material_subtotal

                + stage.labour_cost

                + stage.transport_cost

            )

        )

        < 0.000001

    )



    print("Stage pricing: PASS")



    # --------------------------------------------------------

    # Test overall totals

    # --------------------------------------------------------



    stage_one = StagePricingResult(

        stage_number=1,

        stage_name="Foundation / Footing",

        material_subtotal=1000,

        labour_cost=120,

        transport_cost=50,

        stage_total=1170,

    )



    stage_two = StagePricingResult(

        stage_number=2,

        stage_name="Slab",

        material_subtotal=2000,

        labour_cost=240,

        transport_cost=100,

        stage_total=2340,

    )



    total = calculate_overall_totals(

        [stage_one, stage_two]

    )



    assert (

        abs(total.materials_total - 3000)

        < 0.000001

    )



    assert (

        abs(total.labour_total - 360)

        < 0.000001

    )



    assert (

        abs(total.transport_total - 150)

        < 0.000001

    )



    assert (

        abs(total.grand_total - 3510)

        < 0.000001

    )



    print("Overall totals: PASS")



    # --------------------------------------------------------

    # Test transport

    # --------------------------------------------------------



    transport = calculate_transport_cost(

        material_subtotal=1000,

        location_profile="growth_point",

        distance_km=10,

    )



    assert transport >= 0



    print("Transport calculation: PASS")



    # --------------------------------------------------------

    # Test invalid distance

    # --------------------------------------------------------



    try:



        calculate_transport_cost(

            material_subtotal=1000,

            location_profile="growth_point",

            distance_km=-1,

        )



        raise AssertionError(

            "Negative distance should fail"

        )



    except ValueError:



        pass



    print("Invalid distance handling: PASS")



    print()

    print("=" * 72)

    print("ALL PRICING INTEGRATION TESTS PASSED")

    print("=" * 72)





# ============================================================

# MAIN

# ============================================================



if __name__ == "__main__":
    result = calculate_complete_stage_pricing()
    print_complete_result(result)


