from .location_profiles import (
    LocationPricingProfile,
    get_location_profile,
)
from .models import PriceRecord


def calculate_location_adjusted_price(
    price_record: PriceRecord,
    location_profile: LocationPricingProfile,
) -> float:
    """
    Calculate a material's price after applying a location
    pricing adjustment.

    Formula:

        adjusted_price =
            base_price × (1 + adjustment_percentage / 100)

    The original PriceRecord is not modified.
    """

    if price_record.price < 0:
        raise ValueError(
            "Base material price cannot be negative."
        )

    adjusted_price = (
        price_record.price
        * (
            1
            + location_profile.adjustment_percentage
            / 100
        )
    )

    return adjusted_price


def calculate_location_adjusted_price_by_id(
    price_record: PriceRecord,
    location_profile_id: str,
) -> float:
    """
    Calculate a location-adjusted material price using
    a registered location profile ID.
    """

    location_profile = get_location_profile(
        location_profile_id
    )

    return calculate_location_adjusted_price(
        price_record=price_record,
        location_profile=location_profile,
    )