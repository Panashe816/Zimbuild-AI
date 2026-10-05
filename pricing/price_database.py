from typing import Dict

from .models import PriceRecord, TransportRate


# ============================================================
# MATERIAL PRICE DATABASE
# ============================================================

PRICE_DATABASE: Dict[str, PriceRecord] = {

    # --------------------------------------------------------
    # MASONRY
    # --------------------------------------------------------

    "standard_brick": PriceRecord(
        material_id="standard_brick",
        material_name="Standard brick",
        category="Masonry",
        price=0.15,
        unit="brick",
        currency="USD",
    ),

    "brick_force": PriceRecord(
        material_id="brick_force",
        material_name="Brick force",
        category="Masonry",
        price=1.50,
        unit="m",
        currency="USD",
    ),

    # --------------------------------------------------------
    # WINDOWS AND DOORS
    # --------------------------------------------------------

    "window_unit": PriceRecord(
        material_id="window_unit",
        material_name="Window unit",
        category="Openings",
        price=30.00,
        unit="window",
        currency="USD",
    ),

    "door_unit": PriceRecord(
        material_id="door_unit",
        material_name="Door unit",
        category="Openings",
        price=50.00,
        unit="door",
        currency="USD",
    ),

    # --------------------------------------------------------
    # CEMENT
    # --------------------------------------------------------

    "cement_50kg": PriceRecord(
        material_id="cement_50kg",
        material_name="Cement",
        category="Cement",
        price=13.00,
        unit="50kg_bag",
        currency="USD",
    ),

    # --------------------------------------------------------
    # AGGREGATES / SAND
    # --------------------------------------------------------

    "building_sand": PriceRecord(
        material_id="building_sand",
        material_name="Building sand",
        category="Aggregates",
        price=50.00,
        unit="m3",
        currency="USD",
    ),

    "quarry_stone": PriceRecord(
        material_id="quarry_stone",
        material_name="Quarry stone",
        category="Aggregates",
        price=30.00,
        unit="m3",
        currency="USD",
    ),

    "quarry_dust": PriceRecord(
        material_id="quarry_dust",
        material_name="Quarry dust",
        category="Aggregates",
        price=16.00,
        unit="m3",
        currency="USD",
    ),

    # --------------------------------------------------------
    # WATER
    # --------------------------------------------------------

    "construction_water": PriceRecord(
        material_id="construction_water",
        material_name="Construction water",
        category="Water",
        price=35.00,
        unit="10000_litres",
        currency="USD",
    ),

    # --------------------------------------------------------
    # REINFORCEMENT
    # --------------------------------------------------------

    "reinforcement_steel": PriceRecord(
        material_id="reinforcement_steel",
        material_name="Reinforcement steel",
        category="Reinforcement",
        price=1.80,
        unit="kg",
        currency="USD",
    ),

    "reinforcement_mesh": PriceRecord(
        material_id="reinforcement_mesh",
        material_name="Reinforcement mesh",
        category="Reinforcement",
        price=18.00,
        unit="sheet",
        currency="USD",
    ),

    "binding_wire": PriceRecord(
        material_id="binding_wire",
        material_name="Binding wire",
        category="Reinforcement",
        price=2.50,
        unit="kg",
        currency="USD",
    ),

    # --------------------------------------------------------
    # FOUNDATION / SLAB
    # --------------------------------------------------------

    "hardcore": PriceRecord(
        material_id="hardcore",
        material_name="Hardcore",
        category="Foundation",
        price=25.00,
        unit="m3",
        currency="USD",
    ),

    "dpm": PriceRecord(
        material_id="dpm",
        material_name="Damp-proof membrane",
        category="Foundation",
        price=2.50,
        unit="m2",
        currency="USD",
    ),

    "dpc": PriceRecord(
        material_id="dpc",
        material_name="Damp-proof course",
        category="Masonry",
        price=1.20,
        unit="m",
        currency="USD",
    ),

    # --------------------------------------------------------
    # LINTELS / FORMWORK
    # --------------------------------------------------------

    "lintel": PriceRecord(
        material_id="lintel",
        material_name="Lintel",
        category="Structural",
        price=12.00,
        unit="m",
        currency="USD",
    ),

    "formwork_timber": PriceRecord(
        material_id="formwork_timber",
        material_name="Formwork timber",
        category="Timber",
        price=4.00,
        unit="m",
        currency="USD",
    ),

    "nails": PriceRecord(
        material_id="nails",
        material_name="Nails",
        category="Hardware",
        price=2.50,
        unit="kg",
        currency="USD",
    ),

    # --------------------------------------------------------
    # ROOFING
    # --------------------------------------------------------

    "fibre_cement_sheet": PriceRecord(
        material_id="fibre_cement_sheet",
        material_name="Fibre-cement roofing sheet",
        category="Roofing",
        price=24.00,
        unit="sheet",
        currency="USD",
    ),

    "timber_pole_6m": PriceRecord(
        material_id="timber_pole_6m",
        material_name="Timber pole",
        category="Timber",
        price=10.00,
        unit="6m_pole",
        currency="USD",
    ),

    "roofing_timber": PriceRecord(
        material_id="roofing_timber",
        material_name="Roofing timber",
        category="Roofing",
        price=5.00,
        unit="m",
        currency="USD",
    ),

    "ridge_cap": PriceRecord(
        material_id="ridge_cap",
        material_name="Ridge cap",
        category="Roofing",
        price=8.00,
        unit="m",
        currency="USD",
    ),

    "fascia": PriceRecord(
        material_id="fascia",
        material_name="Fascia board",
        category="Roofing",
        price=6.00,
        unit="m",
        currency="USD",
    ),
}


# ============================================================
# TRANSPORT RATES
# ============================================================

TRANSPORT_RATES: Dict[str, TransportRate] = {

    # --------------------------------------------------------
    # CITY
    # --------------------------------------------------------

    "city": TransportRate(
        price_per_load_per_km=12.00,
        currency="USD",
    ),

    # --------------------------------------------------------
    # BIG TOWN
    #
    # Uses the existing city/big-town rate.
    # --------------------------------------------------------

    "big_town": TransportRate(
        price_per_load_per_km=12.00,
        currency="USD",
    ),

    # --------------------------------------------------------
    # SMALL TOWN
    #
    # Uses the existing growth-point/small-town rate.
    # --------------------------------------------------------

    "small_town": TransportRate(
        price_per_load_per_km=8.00,
        currency="USD",
    ),

    # --------------------------------------------------------
    # GROWTH POINT
    # --------------------------------------------------------

    "growth_point": TransportRate(
        price_per_load_per_km=8.00,
        currency="USD",
    ),

    # --------------------------------------------------------
    # RURAL / FARM
    # --------------------------------------------------------

    "rural_farm": TransportRate(
        price_per_load_per_km=5.00,
        currency="USD",
    ),

    # --------------------------------------------------------
    # LEGACY PROFILE
    #
    # Kept so existing code using "city_town" does not break.
    # --------------------------------------------------------

    "city_town": TransportRate(
        price_per_load_per_km=12.00,
        currency="USD",
    ),
}


# ============================================================
# DEFAULT TRANSPORT RATE
# ============================================================

DEFAULT_TRANSPORT_RATE = TRANSPORT_RATES["city"]


# ============================================================
# MATERIAL PRICE LOOKUP
# ============================================================

def get_price(
    material_id: str,
) -> PriceRecord:
    """
    Retrieve a material price record using its material ID.
    """

    try:

        return PRICE_DATABASE[
            material_id
        ]

    except KeyError as exc:

        raise ValueError(
            f"No price record found for material "
            f"'{material_id}'."
        ) from exc


# ============================================================
# TRANSPORT RATE LOOKUP
# ============================================================

def get_transport_rate(
    location_profile_id: str = "city",
) -> TransportRate:
    """
    Retrieve the transport rate for a location profile.

    Supported profiles:

        city
        big_town
        small_town
        growth_point
        rural_farm

    Legacy profile:

        city_town
    """

    try:

        return TRANSPORT_RATES[
            location_profile_id
        ]

    except KeyError as exc:

        available = ", ".join(
            TRANSPORT_RATES.keys()
        )

        raise ValueError(
            f"No transport rate found for "
            f"location profile "
            f"'{location_profile_id}'. "
            f"Available profiles: {available}"
        ) from exc


# ============================================================
# PRICE DATABASE VALIDATION
# ============================================================

def validate_price_database() -> bool:
    """
    Validate that all required material prices exist.
    """

    required_materials = [

        "standard_brick",

        "brick_force",

        "window_unit",

        "door_unit",

        "cement_50kg",

        "building_sand",

        "quarry_stone",

        "quarry_dust",

        "construction_water",

        "reinforcement_steel",

        "reinforcement_mesh",

        "binding_wire",

        "hardcore",

        "dpm",

        "dpc",

        "lintel",

        "formwork_timber",

        "nails",

        "fibre_cement_sheet",

        "timber_pole_6m",

        "roofing_timber",

        "ridge_cap",

        "fascia",
    ]

    missing = [

        material_id

        for material_id
        in required_materials

        if material_id
        not in PRICE_DATABASE
    ]

    if missing:

        raise ValueError(
            "Missing required material prices: "
            + ", ".join(missing)
        )

    return True


# ============================================================
# STANDALONE TESTS
# ============================================================

def _run_self_tests() -> None:

    print("=" * 70)

    print(
        "PRICE DATABASE TESTS"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Validate material catalogue
    # --------------------------------------------------------

    assert (
        validate_price_database()
        is True
    )

    print(
        "Required material catalogue: PASS"
    )

    # --------------------------------------------------------
    # Verify existing material prices
    # --------------------------------------------------------

    assert (
        get_price(
            "standard_brick"
        ).price
        == 0.15
    )

    print(
        "Standard brick price: PASS"
    )

    assert (
        get_price(
            "brick_force"
        ).price
        == 1.50
    )

    print(
        "Brick force price: PASS"
    )

    assert (
        get_price(
            "cement_50kg"
        ).price
        == 13.00
    )

    print(
        "Cement price: PASS"
    )

    assert (
        get_price(
            "building_sand"
        ).price
        == 50.00
    )

    print(
        "Building sand price: PASS"
    )

    assert (
        get_price(
            "quarry_stone"
        ).price
        == 30.00
    )

    print(
        "Quarry stone price: PASS"
    )

    assert (
        get_price(
            "construction_water"
        ).price
        == 35.00
    )

    print(
        "Construction water price: PASS"
    )

    # --------------------------------------------------------
    # Verify windows and doors
    # --------------------------------------------------------

    assert (
        get_price(
            "window_unit"
        ).price
        == 30.00
    )

    assert (
        get_price(
            "window_unit"
        ).unit
        == "window"
    )

    print(
        "Window unit price: PASS"
    )

    assert (
        get_price(
            "door_unit"
        ).price
        == 50.00
    )

    assert (
        get_price(
            "door_unit"
        ).unit
        == "door"
    )

    print(
        "Door unit price: PASS"
    )

    # --------------------------------------------------------
    # Verify roofing prices remain available
    # --------------------------------------------------------

    assert (
        get_price(
            "fibre_cement_sheet"
        ).price
        == 24.00
    )

    print(
        "Fibre-cement roofing sheet price: PASS"
    )

    assert (
        get_price(
            "timber_pole_6m"
        ).price
        == 10.00
    )

    print(
        "Timber pole price: PASS"
    )

    # --------------------------------------------------------
    # Verify transport rates
    # --------------------------------------------------------

    assert (
        get_transport_rate(
            "city"
        ).price_per_load_per_km
        == 12.00
    )

    assert (
        get_transport_rate(
            "big_town"
        ).price_per_load_per_km
        == 12.00
    )

    assert (
        get_transport_rate(
            "small_town"
        ).price_per_load_per_km
        == 8.00
    )

    assert (
        get_transport_rate(
            "growth_point"
        ).price_per_load_per_km
        == 8.00
    )

    assert (
        get_transport_rate(
            "rural_farm"
        ).price_per_load_per_km
        == 5.00
    )

    # Legacy compatibility

    assert (
        get_transport_rate(
            "city_town"
        ).price_per_load_per_km
        == 12.00
    )

    print(
        "Transport rates: PASS"
    )

    # --------------------------------------------------------
    # Verify invalid material
    # --------------------------------------------------------

    try:

        get_price(
            "material_that_does_not_exist"
        )

        raise AssertionError(
            "Expected ValueError was not raised."
        )

    except ValueError:

        pass

    print(
        "Invalid material handling: PASS"
    )

    # --------------------------------------------------------
    # Verify invalid transport profile
    # --------------------------------------------------------

    try:

        get_transport_rate(
            "invalid_location"
        )

        raise AssertionError(
            "Expected ValueError was not raised."
        )

    except ValueError:

        pass

    print(
        "Invalid transport profile handling: PASS"
    )

    print("-" * 70)

    print(
        "ALL PRICE DATABASE TESTS PASSED"
    )

    print("-" * 70)


# ============================================================
# MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    _run_self_tests()