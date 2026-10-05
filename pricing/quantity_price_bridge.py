"""
ZimBuild AI - Quantity to Price Bridge

Converts construction quantities produced by the quantity
calculation engine into the purchasing units used by the
existing ZimBuild AI price database.

This module does NOT replace the pricing system.

It only handles unit conversion before quantities are passed
to the existing pricing calculators.
"""

from math import ceil
from typing import Dict


# ============================================================
# PROJECT PRICING / CONVERSION STANDARDS
# ============================================================

# Construction water
WATER_PRICE_UNIT_LITRES = 10000.0


# Reinforcement steel
#
# 12 mm reinforcement bar:
#
# Weight per metre = d² / 162
#                 = 12² / 162
#                 = 0.8889 kg/m
#
STEEL_DIAMETER_MM = 12.0
STEEL_KG_PER_METRE = (
    STEEL_DIAMETER_MM ** 2
) / 162.0


# Reinforcement mesh
#
# Standard assumed sheet:
#
# 2.4 m × 4.8 m
#
MESH_SHEET_LENGTH_M = 4.8
MESH_SHEET_WIDTH_M = 2.4

MESH_SHEET_AREA_M2 = (
    MESH_SHEET_LENGTH_M
    * MESH_SHEET_WIDTH_M
)


# Binding wire
#
# Binding wire allowance:
# 1.5% of reinforcement steel weight
#
BINDING_WIRE_PERCENTAGE = 1.5


# ============================================================
# BASIC VALIDATION
# ============================================================

def _validate_quantity(
    quantity: float,
    name: str,
) -> float:

    if quantity < 0:
        raise ValueError(
            f"{name} quantity cannot be negative."
        )

    return float(quantity)


# ============================================================
# WATER
# ============================================================

def litres_to_price_units(
    litres: float,
) -> float:
    """
    Convert construction water from litres into the
    purchasing unit used by the price database.

    Price database unit:
        10,000 litres
    """

    litres = _validate_quantity(
        litres,
        "Construction water",
    )

    return litres / WATER_PRICE_UNIT_LITRES


# ============================================================
# REINFORCEMENT STEEL
# ============================================================

def steel_metres_to_kg(
    metres: float,
) -> float:
    """
    Convert 12 mm reinforcement steel from metres to kg.

    Formula:

        kg/m = diameter² / 162

    For 12 mm steel:

        12² / 162 = 0.8889 kg/m
    """

    metres = _validate_quantity(
        metres,
        "Reinforcement steel",
    )

    return metres * STEEL_KG_PER_METRE


# ============================================================
# REINFORCEMENT MESH
# ============================================================

def mesh_m2_to_sheets(
    area_m2: float,
) -> float:
    """
    Convert reinforcement mesh area into complete sheets.

    One assumed sheet:

        2.4 m × 4.8 m
        = 11.52 m²

    Sheets are rounded up because a partial sheet must be
    purchased as a complete sheet.
    """

    area_m2 = _validate_quantity(
        area_m2,
        "Reinforcement mesh",
    )

    if area_m2 == 0:
        return 0.0

    return ceil(
        area_m2 / MESH_SHEET_AREA_M2
    )


# ============================================================
# BINDING WIRE
# ============================================================

def calculate_binding_wire_kg(
    steel_kg: float,
) -> float:
    """
    Calculate binding wire quantity.

    Binding wire allowance:

        1.5% of reinforcement steel weight
    """

    steel_kg = _validate_quantity(
        steel_kg,
        "Reinforcement steel",
    )

    return (
        steel_kg
        * BINDING_WIRE_PERCENTAGE
        / 100.0
    )


# ============================================================
# GENERAL MATERIAL QUANTITY CONVERSION
# ============================================================

def convert_material_quantity(
    material_id: str,
    quantity: float,
) -> float:
    """
    Convert a material quantity into the purchasing unit
    expected by the price database.

    Materials that already use compatible units are returned
    unchanged.
    """

    quantity = _validate_quantity(
        quantity,
        material_id,
    )

    # --------------------------------------------------------
    # Water
    # --------------------------------------------------------

    if material_id == "construction_water":
        return litres_to_price_units(
            quantity
        )

    # --------------------------------------------------------
    # Reinforcement steel
    # --------------------------------------------------------

    if material_id == "reinforcement_steel":
        return steel_metres_to_kg(
            quantity
        )

    # --------------------------------------------------------
    # Reinforcement mesh
    # --------------------------------------------------------

    if material_id == "reinforcement_mesh":
        return mesh_m2_to_sheets(
            quantity
        )

    # --------------------------------------------------------
    # All other materials
    # --------------------------------------------------------

    return quantity


# ============================================================
# CONVERT COMPLETE MATERIAL QUANTITY DICTIONARY
# ============================================================

def convert_material_quantities(
    quantities: Dict[str, float],
) -> Dict[str, float]:
    """
    Convert a dictionary of material quantities.

    Example input:

        {
            "standard_brick": 15344,
            "cement_50kg": 87,
            "construction_water": 2533.58,
            "reinforcement_steel": 171.795,
            "reinforcement_mesh": 199.43
        }

    Returns quantities in the purchasing units required
    by the price database.
    """

    converted = {}

    for material_id, quantity in quantities.items():

        converted[material_id] = (
            convert_material_quantity(
                material_id,
                quantity,
            )
        )

    # --------------------------------------------------------
    # Binding wire
    # --------------------------------------------------------
    #
    # Binding wire depends on reinforcement steel.
    #
    if "reinforcement_steel" in converted:

        steel_kg = converted[
            "reinforcement_steel"
        ]

        converted[
            "binding_wire"
        ] = calculate_binding_wire_kg(
            steel_kg
        )

    return converted


# ============================================================
# PRICE-READY MATERIAL RECORD
# ============================================================

def build_price_ready_quantities(
    quantities: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    """
    Return a detailed price-ready dictionary.

    This makes the conversion transparent for debugging
    and for later BOQ generation.
    """

    converted = convert_material_quantities(
        quantities
    )

    result = {}

    for material_id, original_quantity in quantities.items():

        result[material_id] = {
            "original_quantity": float(
                original_quantity
            ),
            "price_quantity": converted[
                material_id
            ],
        }

    # Binding wire may have been derived rather than
    # supplied directly.
    if "binding_wire" in converted:

        if "binding_wire" not in result:

            result["binding_wire"] = {
                "original_quantity": 0.0,
                "price_quantity": converted[
                    "binding_wire"
                ],
            }

    return result


# ============================================================
# STANDALONE TESTS
# ============================================================

def _run_self_tests() -> None:

    print("=" * 70)
    print("QUANTITY → PRICE BRIDGE TESTS")
    print("=" * 70)

    # --------------------------------------------------------
    # Water
    # --------------------------------------------------------

    water = litres_to_price_units(
        10000
    )

    assert water == 1.0

    print(
        "Water litres → 10,000-litre unit: PASS"
    )

    # --------------------------------------------------------
    # Steel
    # --------------------------------------------------------

    steel = steel_metres_to_kg(
        100.0
    )

    assert round(
        steel,
        3
    ) == 88.889

    print(
        "12 mm steel metres → kg: PASS"
    )

    # --------------------------------------------------------
    # Mesh
    # --------------------------------------------------------

    mesh = mesh_m2_to_sheets(
        11.52
    )

    assert mesh == 1

    print(
        "Mesh m² → sheets: PASS"
    )

    mesh_large = mesh_m2_to_sheets(
        20.0
    )

    assert mesh_large == 2

    print(
        "Mesh sheet rounding: PASS"
    )

    # --------------------------------------------------------
    # Binding wire
    # --------------------------------------------------------

    wire = calculate_binding_wire_kg(
        100.0
    )

    assert wire == 1.5

    print(
        "Binding wire allowance: PASS"
    )

    # --------------------------------------------------------
    # Direct quantities
    # --------------------------------------------------------

    brick = convert_material_quantity(
        "standard_brick",
        1000
    )

    assert brick == 1000

    print(
        "Direct material quantity: PASS"
    )

    # --------------------------------------------------------
    # Complete dictionary
    # --------------------------------------------------------

    quantities = {
        "standard_brick": 15344,
        "cement_50kg": 87,
        "building_sand": 6.193,
        "construction_water": 2533.58,
        "reinforcement_steel": 100.0,
        "reinforcement_mesh": 199.43,
    }

    converted = convert_material_quantities(
        quantities
    )

    assert (
        converted["standard_brick"]
        == 15344
    )

    assert (
        converted["cement_50kg"]
        == 87
    )

    assert round(
        converted["construction_water"],
        5,
    ) == round(
        2533.58 / 10000,
        5,
    )

    assert round(
        converted["reinforcement_steel"],
        3,
    ) == 88.889

    assert (
        converted["reinforcement_mesh"]
        == 18
    )

    assert round(
        converted["binding_wire"],
        3,
    ) == 1.333

    print(
        "Complete material conversion: PASS"
    )

    # --------------------------------------------------------
    # Price-ready output
    # --------------------------------------------------------

    ready = build_price_ready_quantities(
        quantities
    )

    assert (
        ready["standard_brick"]
        ["price_quantity"]
        == 15344
    )

    assert (
        "binding_wire"
        in ready
    )

    print(
        "Price-ready material records: PASS"
    )

    print("-" * 70)
    print(
        "ALL QUANTITY → PRICE BRIDGE TESTS PASSED"
    )
    print("-" * 70)


# ============================================================
# MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    _run_self_tests()