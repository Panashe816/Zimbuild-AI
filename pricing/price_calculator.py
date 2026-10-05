from .models import MaterialCost, PriceRecord
from .price_database import get_price


def calculate_material_cost(
    material_id: str,
    quantity: float,
) -> MaterialCost:
    """
    Calculate the cost of a material using the registered
    price in the ZimBuild AI price database.

    The quantity must use the same purchasing unit as the
    corresponding PriceRecord.

    Examples:

        1000 bricks
        → material_id = "standard_brick"

        20 cement bags
        → material_id = "cement_50kg"
    """

    if quantity < 0:
        raise ValueError(
            "Material quantity cannot be negative."
        )

    price_record: PriceRecord = get_price(
        material_id
    )

    material_cost = (
        quantity
        * price_record.price
    )

    return MaterialCost(
        material_name=price_record.material_name,
        quantity=quantity,
        unit=price_record.unit,
        unit_price=price_record.price,
        material_cost=material_cost,
        currency=price_record.currency,
        transport_cost=0.0,
    )


def calculate_material_cost_from_price(
    price_record: PriceRecord,
    quantity: float,
) -> MaterialCost:
    """
    Calculate material cost directly from a PriceRecord.

    This function is useful when the pricing engine already
    has a specific price record available.
    """

    if quantity < 0:
        raise ValueError(
            "Material quantity cannot be negative."
        )

    material_cost = (
        quantity
        * price_record.price
    )

    return MaterialCost(
        material_name=price_record.material_name,
        quantity=quantity,
        unit=price_record.unit,
        unit_price=price_record.price,
        material_cost=material_cost,
        currency=price_record.currency,
        transport_cost=0.0,
    )