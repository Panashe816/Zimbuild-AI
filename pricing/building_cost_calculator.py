"""
ZimBuild AI - Building Cost Calculator
======================================

Phase 11 pricing engine.

This module converts construction material quantities into
priced construction costs.

Responsibilities
----------------
    1. Map material IDs to the price database.
    2. Convert construction quantities into purchasing units.
    3. Apply location-based pricing.
    4. Calculate individual material costs.
    5. Track materials without prices.
    6. Calculate transport costs.
    7. Provide material subtotal and grand total.

Quantity conversion is handled by:
    pricing.quantity_price_bridge

The existing pricing database remains the source of
material prices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from materials.models import MaterialQuantity

from .location_price_calculator import (
    calculate_location_adjusted_price,
)

from .location_profiles import (
    LocationPricingProfile,
    get_location_profile,
)

from .models import (
    MaterialCost,
    TransportRequirement,
    UnpricedMaterial,
)

from .price_database import (
    get_price,
    get_transport_rate,
)

from .quantity_price_bridge import (
    convert_material_quantity,
)

from .transport_calculator import (
    calculate_transport_cost,
)


# ============================================================================
# BUILDING COST SUMMARY
# ============================================================================

@dataclass
class BuildingCostSummary:
    """
    Complete monetary summary for a building estimate.
    """

    material_costs: List[MaterialCost] = field(
        default_factory=list
    )

    unpriced_materials: List[UnpricedMaterial] = field(
        default_factory=list
    )

    currency: str = "USD"

    transport_load_count: int = 0

    transport_distance_km: float = 0.0

    transport_rate_per_load_per_km: float = 0.0

    transport_cost: float = 0.0

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    @property
    def material_count(self) -> int:
        """
        Number of successfully priced materials.
        """

        return len(
            self.material_costs
        )

    @property
    def unpriced_material_count(self) -> int:
        """
        Number of materials without a valid price.
        """

        return len(
            self.unpriced_materials
        )

    # ------------------------------------------------------------------
    # Material subtotal
    # ------------------------------------------------------------------

    @property
    def material_subtotal(self) -> float:
        """
        Total material cost before transport.
        """

        return sum(
            material.material_cost
            for material in self.material_costs
        )

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    @property
    def material_transport_total(self) -> float:
        """
        Transport cost attached directly to material records.
        """

        return sum(
            material.transport_cost
            for material in self.material_costs
        )

    @property
    def transport_total(self) -> float:
        """
        Total transport cost.
        """

        return (
            self.material_transport_total
            + self.transport_cost
        )

    # ------------------------------------------------------------------
    # Grand total
    # ------------------------------------------------------------------

    @property
    def total_cost(self) -> float:
        """
        Material subtotal plus transport.
        """

        return (
            self.material_subtotal
            + self.transport_total
        )

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_material_cost(
        self,
        material_name: str,
    ) -> MaterialCost:
        """
        Retrieve a priced material by name.
        """

        for material in self.material_costs:

            if (
                material.material_name
                == material_name
            ):
                return material

        raise ValueError(
            f"Material cost for "
            f"'{material_name}' was not found."
        )

    def get_unpriced_material(
        self,
        material_name: str,
    ) -> UnpricedMaterial:
        """
        Retrieve an unpriced material by name.
        """

        for material in self.unpriced_materials:

            if (
                material.material_name
                == material_name
            ):
                return material

        raise ValueError(
            f"Unpriced material "
            f"'{material_name}' was not found."
        )


# ============================================================================
# MATERIAL ID MAPPING
# ============================================================================

MATERIAL_ID_MAP = {

    # --------------------------------------------------------
    # Masonry
    # --------------------------------------------------------

    "Standard brick": "standard_brick",

    "Brick force": "brick_force",

    # --------------------------------------------------------
    # Cement
    # --------------------------------------------------------

    "Cement": "cement_50kg",

    # --------------------------------------------------------
    # Aggregates
    # --------------------------------------------------------

    "Building sand": "building_sand",

    "Quarry stone": "quarry_stone",

    "Quarry dust": "quarry_dust",

    # --------------------------------------------------------
    # Water
    # --------------------------------------------------------

    "Construction water": "construction_water",

    # --------------------------------------------------------
    # Openings
    # --------------------------------------------------------

    "Window unit": "window_unit",

    "Door unit": "door_unit",

    # --------------------------------------------------------
    # Reinforcement
    # --------------------------------------------------------

    "Reinforcement steel": "reinforcement_steel",

    "Reinforcement mesh": "reinforcement_mesh",

    "Binding wire": "binding_wire",

    # --------------------------------------------------------
    # Foundation / slab
    # --------------------------------------------------------

    "Hardcore": "hardcore",

    "Damp-proof membrane": "dpm",

    "Damp-proof course": "dpc",

    # --------------------------------------------------------
    # Structural
    # --------------------------------------------------------

    "Lintel": "lintel",

    # --------------------------------------------------------
    # Formwork / hardware
    # --------------------------------------------------------

    "Formwork timber": "formwork_timber",

    "Nails": "nails",

    # --------------------------------------------------------
    # Roofing
    # --------------------------------------------------------

    "Fibre-cement roofing sheet": (
        "fibre_cement_sheet"
    ),

    "Timber pole": "timber_pole_6m",

    "Roofing timber": "roofing_timber",

    "Ridge cap": "ridge_cap",

    "Fascia board": "fascia",
}


# ============================================================================
# MATERIAL ID RESOLUTION
# ============================================================================

def resolve_material_id(
    material: MaterialQuantity,
) -> str | None:
    """
    Resolve a material to its price-database ID.

    The explicit material_id is preferred because it is the
    most reliable identifier.

    The material-name mapping is retained as a compatibility
    fallback.
    """

    # --------------------------------------------------------
    # Preferred: explicit material ID
    # --------------------------------------------------------

    explicit_id = getattr(
        material,
        "material_id",
        None,
    )

    if explicit_id:

        return str(
            explicit_id
        )

    # --------------------------------------------------------
    # Fallback: material name
    # --------------------------------------------------------

    material_name = getattr(
        material,
        "material_name",
        "",
    )

    return MATERIAL_ID_MAP.get(
        material_name
    )


# ============================================================================
# MATERIAL COST CALCULATION
# ============================================================================

def _calculate_material_cost(
    material: MaterialQuantity,
    location_profile: LocationPricingProfile,
) -> MaterialCost | UnpricedMaterial:
    """
    Calculate the cost of one material.

    The material quantity is first converted into the purchasing
    unit expected by the price database.

    Examples:

        litres
            -> 10,000-litre pricing units

        reinforcement steel metres
            -> kg

        reinforcement mesh m²
            -> sheets

        compatible quantities
            -> unchanged
    """

    material_id = resolve_material_id(
        material
    )

    # --------------------------------------------------------
    # No mapping
    # --------------------------------------------------------

    if material_id is None:

        return UnpricedMaterial(
            material_name=(
                material.material_name
            ),
            quantity=material.quantity,
            unit=material.unit,
            reason=(
                "No exact price mapping "
                "is currently configured."
            ),
        )

    # --------------------------------------------------------
    # Price lookup
    # --------------------------------------------------------

    try:

        price_record = get_price(
            material_id
        )

    except ValueError:

        return UnpricedMaterial(
            material_name=(
                material.material_name
            ),
            quantity=material.quantity,
            unit=material.unit,
            reason=(
                "No exact price is currently "
                "available in the price database."
            ),
        )

    # --------------------------------------------------------
    # Quantity conversion
    # --------------------------------------------------------

    try:

        price_quantity = (
            convert_material_quantity(
                material_id=material_id,
                quantity=material.quantity,
            )
        )

    except ValueError as exc:

        return UnpricedMaterial(
            material_name=(
                material.material_name
            ),
            quantity=material.quantity,
            unit=material.unit,
            reason=(
                f"Quantity conversion failed: {exc}"
            ),
        )

    # --------------------------------------------------------
    # Location adjustment
    # --------------------------------------------------------

    adjusted_price = (
        calculate_location_adjusted_price(
            price_record,
            location_profile,
        )
    )

    # --------------------------------------------------------
    # Material cost
    # --------------------------------------------------------

    material_cost = (
        price_quantity
        * adjusted_price
    )

    return MaterialCost(
        material_name=(
            price_record.material_name
        ),
        quantity=price_quantity,
        unit=price_record.unit,
        unit_price=adjusted_price,
        material_cost=material_cost,
        currency=price_record.currency,
        transport_cost=0.0,
    )


# ============================================================================
# MAIN BUILDING COST CALCULATOR
# ============================================================================

def calculate_building_cost(
    material_summary,
    location_profile_id: str = "growth_point",
    transport_load_count: int = 0,
    transport_distance_km: float = 0.0,
) -> BuildingCostSummary:
    """
    Calculate the complete monetary cost of the supplied
    materials.

    Parameters
    ----------
    material_summary:
        Can be either:

            - a list/iterable of MaterialQuantity objects
            - an object exposing a 'materials' attribute

        This keeps compatibility with the earlier Phase 10
        interface.

    location_profile_id:
        Location pricing profile.

    transport_load_count:
        Number of transport loads.

    transport_distance_km:
        Transport distance in kilometres.

    Returns
    -------
    BuildingCostSummary
        Complete material and transport cost summary.
    """

    # ==================================================================
    # LOCATION
    # ==================================================================

    location_profile: LocationPricingProfile = (
        get_location_profile(
            location_profile_id
        )
    )

    # ==================================================================
    # VALIDATION
    # ==================================================================

    if transport_load_count < 0:

        raise ValueError(
            "Transport load count cannot be negative."
        )

    if transport_distance_km < 0:

        raise ValueError(
            "Transport distance cannot be negative."
        )

    # ==================================================================
    # NORMALISE MATERIAL INPUT
    # ==================================================================

    if material_summary is None:

        materials: List[MaterialQuantity] = []

    elif hasattr(
        material_summary,
        "materials",
    ):

        materials = list(
            material_summary.materials
        )

    else:

        materials = list(
            material_summary
        )

    # ==================================================================
    # MATERIAL COSTS
    # ==================================================================

    material_costs: List[MaterialCost] = []

    unpriced_materials: List[
        UnpricedMaterial
    ] = []

    for material in materials:

        # --------------------------------------------------------------
        # Ignore invalid entries safely
        # --------------------------------------------------------------

        if material is None:
            continue

        # --------------------------------------------------------------
        # Calculate price
        # --------------------------------------------------------------

        result = _calculate_material_cost(
            material=material,
            location_profile=location_profile,
        )

        # --------------------------------------------------------------
        # Store result
        # --------------------------------------------------------------

        if isinstance(
            result,
            MaterialCost,
        ):

            material_costs.append(
                result
            )

        else:

            unpriced_materials.append(
                result
            )

    # ==================================================================
    # TRANSPORT
    # ==================================================================

    transport_rate = get_transport_rate(
        location_profile_id
    )

    transport_requirement = (
        TransportRequirement(
            load_count=transport_load_count,
            distance_km=(
                transport_distance_km
            ),
        )
    )

    transport_cost = (
        calculate_transport_cost(
            requirement=(
                transport_requirement
            ),
            rate=transport_rate,
        )
    )

    # ==================================================================
    # FINAL SUMMARY
    # ==================================================================

    return BuildingCostSummary(

        material_costs=material_costs,

        unpriced_materials=(
            unpriced_materials
        ),

        currency="USD",

        transport_load_count=(
            transport_load_count
        ),

        transport_distance_km=(
            transport_distance_km
        ),

        transport_rate_per_load_per_km=(
            transport_rate.price_per_load_per_km
        ),

        transport_cost=transport_cost,
    )


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def calculate_material_costs(
    materials: Iterable[MaterialQuantity],
    location_profile_id: str = "growth_point",
) -> BuildingCostSummary:
    """
    Convenience wrapper for callers that already have a
    material list.
    """

    return calculate_building_cost(
        material_summary=list(
            materials
        ),
        location_profile_id=(
            location_profile_id
        ),
    )


# ============================================================================
# SELF TESTS
# ============================================================================

def _run_self_tests() -> None:
    """
    Standalone Phase 11 building-cost tests.
    """

    print("=" * 70)
    print("BUILDING COST CALCULATOR TESTS")
    print("=" * 70)

    # ==================================================================
    # TEST MATERIAL LIST
    # ==================================================================

    materials = [

        MaterialQuantity(
            material_name="Standard brick",
            quantity=1000,
            unit="brick",
            material_id="standard_brick",
            category="Masonry",
        ),

        MaterialQuantity(
            material_name="Brick force",
            quantity=100,
            unit="m",
            material_id="brick_force",
            category="Masonry",
        ),

        MaterialQuantity(
            material_name="Cement",
            quantity=5,
            unit="bag",
            material_id="cement_50kg",
            category="Cement",
        ),

        MaterialQuantity(
            material_name="Building sand",
            quantity=2,
            unit="m3",
            material_id="building_sand",
            category="Aggregates",
        ),

        MaterialQuantity(
            material_name="Quarry stone",
            quantity=3,
            unit="m3",
            material_id="quarry_stone",
            category="Aggregates",
        ),

        MaterialQuantity(
            material_name="Construction water",
            quantity=10000,
            unit="litres",
            material_id="construction_water",
            category="Water",
        ),

        MaterialQuantity(
            material_name="Reinforcement steel",
            quantity=100,
            unit="m",
            material_id="reinforcement_steel",
            category="Reinforcement",
        ),

        MaterialQuantity(
            material_name="Reinforcement mesh",
            quantity=11.52,
            unit="m2",
            material_id="reinforcement_mesh",
            category="Reinforcement",
        ),

        MaterialQuantity(
            material_name="Binding wire",
            quantity=2,
            unit="kg",
            material_id="binding_wire",
            category="Reinforcement",
        ),

        MaterialQuantity(
            material_name="Hardcore",
            quantity=5,
            unit="m3",
            material_id="hardcore",
            category="Foundation",
        ),

        MaterialQuantity(
            material_name="Damp-proof membrane",
            quantity=50,
            unit="m2",
            material_id="dpm",
            category="Foundation",
        ),

        MaterialQuantity(
            material_name="Damp-proof course",
            quantity=100,
            unit="m",
            material_id="dpc",
            category="Masonry",
        ),

        MaterialQuantity(
            material_name="Lintel",
            quantity=10,
            unit="m",
            material_id="lintel",
            category="Structural",
        ),

        MaterialQuantity(
            material_name=(
                "Fibre-cement roofing sheet"
            ),
            quantity=20,
            unit="sheet",
            material_id=(
                "fibre_cement_sheet"
            ),
            category="Roofing",
        ),

        MaterialQuantity(
            material_name="Timber pole",
            quantity=10,
            unit="pole",
            material_id="timber_pole_6m",
            category="Timber",
        ),

        MaterialQuantity(
            material_name="Window unit",
            quantity=11,
            unit="window",
            material_id="window_unit",
            category="Openings",
        ),

        MaterialQuantity(
            material_name="Door unit",
            quantity=8,
            unit="door",
            material_id="door_unit",
            category="Openings",
        ),
    ]

    # ==================================================================
    # CALCULATE COST
    # ==================================================================

    summary = calculate_building_cost(
        material_summary=materials,
        location_profile_id="growth_point",
        transport_load_count=2,
        transport_distance_km=10,
    )

    # ==================================================================
    # MATERIAL COUNT
    # ==================================================================

    assert (
        summary.material_count == 17
    )

    print(
        "Material pricing count: PASS"
    )

    # ==================================================================
    # NO UNPRICED MATERIALS
    # ==================================================================

    assert (
        summary.unpriced_material_count == 0
    )

    print(
        "All test materials priced: PASS"
    )

    # ==================================================================
    # DIRECT MATERIAL PRICES
    # ==================================================================

    brick_cost = (
        summary.get_material_cost(
            "Standard brick"
        )
    )

    assert (
        brick_cost.quantity
        == 1000
    )

    assert (
        brick_cost.unit
        == "brick"
    )

    print(
        "Standard brick pricing: PASS"
    )

    cement_cost = (
        summary.get_material_cost(
            "Cement"
        )
    )

    assert (
        cement_cost.quantity
        == 5
    )

    assert (
        cement_cost.unit
        == "50kg_bag"
    )

    print(
        "Cement pricing: PASS"
    )

    sand_cost = (
        summary.get_material_cost(
            "Building sand"
        )
    )

    assert (
        sand_cost.quantity
        == 2
    )

    print(
        "Building sand pricing: PASS"
    )

    # ==================================================================
    # BRICK FORCE
    # ==================================================================

    brick_force_cost = (
        summary.get_material_cost(
            "Brick force"
        )
    )

    assert (
        brick_force_cost.quantity
        == 100
    )

    assert (
        brick_force_cost.unit
        == "m"
    )

    print(
        "Brick force pricing: PASS"
    )

    # ==================================================================
    # WATER CONVERSION
    # ==================================================================

    water_cost = (
        summary.get_material_cost(
            "Construction water"
        )
    )

    assert (
        water_cost.quantity
        == 1.0
    )

    assert (
        water_cost.unit
        == "10000_litres"
    )

    print(
        "Construction water conversion: PASS"
    )

    # ==================================================================
    # STEEL CONVERSION
    # ==================================================================

    steel_cost = (
        summary.get_material_cost(
            "Reinforcement steel"
        )
    )

    assert round(
        steel_cost.quantity,
        3,
    ) == 88.889

    assert (
        steel_cost.unit
        == "kg"
    )

    print(
        "Reinforcement steel conversion: PASS"
    )

    # ==================================================================
    # MESH CONVERSION
    # ==================================================================

    mesh_cost = (
        summary.get_material_cost(
            "Reinforcement mesh"
        )
    )

    assert (
        mesh_cost.quantity
        == 1
    )

    assert (
        mesh_cost.unit
        == "sheet"
    )

    print(
        "Reinforcement mesh conversion: PASS"
    )

    # ==================================================================
    # BINDING WIRE
    # ==================================================================

    wire_cost = (
        summary.get_material_cost(
            "Binding wire"
        )
    )

    assert (
        wire_cost.quantity
        == 2
    )

    assert (
        wire_cost.unit
        == "kg"
    )

    print(
        "Binding wire pricing: PASS"
    )

    # ==================================================================
    # WINDOW AND DOOR PRICING
    # ==================================================================

    window_cost = (
        summary.get_material_cost(
            "Window unit"
        )
    )

    assert (
        window_cost.quantity == 11
    )

    assert (
        window_cost.unit == "window"
    )

    assert (
        window_cost.unit_price == 30.0
    )

    assert (
        window_cost.material_cost == 330.0
    )

    print(
        "Window unit pricing: PASS"
    )

    door_cost = (
        summary.get_material_cost(
            "Door unit"
        )
    )

    assert (
        door_cost.quantity == 8
    )

    assert (
        door_cost.unit == "door"
    )

    assert (
        door_cost.unit_price == 50.0
    )

    assert (
        door_cost.material_cost == 400.0
    )

    print(
        "Door unit pricing: PASS"
    )

    # ==================================================================
    # TRANSPORT
    # ==================================================================

    # Growth point rate:
    #
    #     $8/load/km
    #
    # 2 loads × 10 km × $8
    #
    #     = $160

    assert (
        summary.transport_cost
        == 160.0
    )

    print(
        "Transport calculation: PASS"
    )

    # ==================================================================
    # TOTALS
    # ==================================================================

    assert (
        summary.material_subtotal
        > 0
    )

    assert (
        summary.total_cost
        > summary.material_subtotal
    )

    print(
        "Material subtotal: PASS"
    )

    print(
        "Grand total calculation: PASS"
    )

    # ==================================================================
    # UNKNOWN MATERIAL TEST
    # ==================================================================

    unknown_material = [

        MaterialQuantity(
            material_name="Unknown material",
            quantity=10,
            unit="unit",
            material_id="unknown_material",
        )

    ]

    unknown_summary = (
        calculate_building_cost(
            material_summary=(
                unknown_material
            ),
            location_profile_id=(
                "growth_point"
            ),
        )
    )

    assert (
        unknown_summary.unpriced_material_count
        == 1
    )

    print(
        "Unpriced material handling: PASS"
    )

    # ==================================================================
    # INVALID TRANSPORT TEST
    # ==================================================================

    try:

        calculate_building_cost(
            material_summary=materials,
            location_profile_id=(
                "growth_point"
            ),
            transport_load_count=-1,
        )

        raise AssertionError(
            "Negative transport loads "
            "were accepted."
        )

    except ValueError:

        pass

    print(
        "Invalid transport handling: PASS"
    )

    # ==================================================================
    # FINAL
    # ==================================================================

    print("-" * 70)

    print(
        "ALL BUILDING COST CALCULATOR TESTS PASSED"
    )

    print("-" * 70)


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    _run_self_tests()