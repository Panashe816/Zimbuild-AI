"""
ZimBuild AI - Location Pricing Profiles
=======================================

Defines the location categories used by the pricing engine.

The current pricing model supports:

    1. City
    2. Big Town
    3. Small Town
    4. Growth Point
    5. Rural / Farm

All current profiles use a material price factor of 1.00.

The legacy adjustment_percentage property is retained for
backward compatibility with the existing location pricing
calculator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ============================================================================
# LOCATION PRICING PROFILE
# ============================================================================

@dataclass(frozen=True)
class LocationPricingProfile:
    """
    Represents a construction location pricing profile.

    Parameters
    ----------
    profile_id:
        Unique identifier for the profile.

    name:
        Human-readable profile name.

    description:
        Description of the location category.

    material_price_factor:
        Multiplication factor applied to material prices.

        Examples:
            1.00 = no adjustment
            1.10 = 10% increase
            0.95 = 5% decrease
    """

    profile_id: str
    name: str
    description: str
    material_price_factor: float = 1.00

    # ------------------------------------------------------------------
    # BACKWARD COMPATIBILITY
    # ------------------------------------------------------------------

    @property
    def adjustment_percentage(self) -> float:
        """
        Return the material price adjustment as a percentage.

        This property exists for compatibility with the existing
        location pricing calculator, which still expects the older
        'adjustment_percentage' attribute.

        Examples
        --------
        material_price_factor = 1.00
            -> 0%

        material_price_factor = 1.10
            -> 10%

        material_price_factor = 0.95
            -> -5%
        """

        return (
            self.material_price_factor - 1.00
        ) * 100.00


# ============================================================================
# LOCATION PROFILE CATALOGUE
# ============================================================================

LOCATION_PROFILES: Dict[str, LocationPricingProfile] = {

    # ------------------------------------------------------------------
    # CITY
    # ------------------------------------------------------------------

    "city": LocationPricingProfile(
        profile_id="city",
        name="City",
        description=(
            "Major urban construction location."
        ),
        material_price_factor=1.00,
    ),

    # ------------------------------------------------------------------
    # BIG TOWN
    # ------------------------------------------------------------------

    "big_town": LocationPricingProfile(
        profile_id="big_town",
        name="Big Town",
        description=(
            "Large urban or regional town."
        ),
        material_price_factor=1.00,
    ),

    # ------------------------------------------------------------------
    # SMALL TOWN
    # ------------------------------------------------------------------

    "small_town": LocationPricingProfile(
        profile_id="small_town",
        name="Small Town",
        description=(
            "Small urban or district town."
        ),
        material_price_factor=1.00,
    ),

    # ------------------------------------------------------------------
    # GROWTH POINT
    # ------------------------------------------------------------------

    "growth_point": LocationPricingProfile(
        profile_id="growth_point",
        name="Growth Point",
        description=(
            "Construction location in a designated "
            "growth point."
        ),
        material_price_factor=1.00,
    ),

    # ------------------------------------------------------------------
    # RURAL / FARM
    # ------------------------------------------------------------------

    "rural_farm": LocationPricingProfile(
        profile_id="rural_farm",
        name="Rural / Farm",
        description=(
            "Rural or farm-based construction location."
        ),
        material_price_factor=1.00,
    ),

    # ------------------------------------------------------------------
    # LEGACY PROFILE
    # ------------------------------------------------------------------

    "city_town": LocationPricingProfile(
        profile_id="city_town",
        name="City / Town",
        description=(
            "Legacy compatibility profile for earlier "
            "versions of the pricing engine."
        ),
        material_price_factor=1.00,
    ),
}


# ============================================================================
# DEFAULT PROFILE
# ============================================================================

DEFAULT_LOCATION_PROFILE_ID = "city"


# ============================================================================
# GET LOCATION PROFILE
# ============================================================================

def get_location_profile(
    profile_id: str = DEFAULT_LOCATION_PROFILE_ID,
) -> LocationPricingProfile:
    """
    Retrieve a location pricing profile.

    Parameters
    ----------
    profile_id:
        ID of the required location profile.

    Returns
    -------
    LocationPricingProfile
        The requested location profile.

    Raises
    ------
    ValueError
        If the requested profile does not exist.
    """

    if profile_id not in LOCATION_PROFILES:

        available = ", ".join(
            sorted(LOCATION_PROFILES.keys())
        )

        raise ValueError(
            f"Unknown location profile "
            f"'{profile_id}'. "
            f"Available profiles: {available}"
        )

    return LOCATION_PROFILES[profile_id]


# ============================================================================
# GET AVAILABLE LOCATION PROFILES
# ============================================================================

def get_available_location_profiles() -> List[
    LocationPricingProfile
]:
    """
    Return all available location profiles.

    Returns
    -------
    list[LocationPricingProfile]
        List of configured location profiles.
    """

    return list(
        LOCATION_PROFILES.values()
    )


# ============================================================================
# VALIDATE LOCATION PROFILES
# ============================================================================

def validate_location_profiles() -> None:
    """
    Validate the location profile catalogue.

    Raises
    ------
    AssertionError
        If any required profile is missing or invalid.
    """

    required_profiles = [
        "city",
        "big_town",
        "small_town",
        "growth_point",
        "rural_farm",
        "city_town",
    ]

    # ------------------------------------------------------------------
    # Required profiles
    # ------------------------------------------------------------------

    for profile_id in required_profiles:

        assert profile_id in LOCATION_PROFILES, (
            f"Missing location profile: "
            f"{profile_id}"
        )

    # ------------------------------------------------------------------
    # Validate profile contents
    # ------------------------------------------------------------------

    for profile in LOCATION_PROFILES.values():

        assert (
            profile.profile_id
            in LOCATION_PROFILES
        )

        assert (
            profile.name.strip()
            != ""
        )

        assert (
            profile.description.strip()
            != ""
        )

        assert (
            profile.material_price_factor
            > 0
        )

        # Backward compatibility check
        assert isinstance(
            profile.adjustment_percentage,
            float,
        )

    # ------------------------------------------------------------------
    # Check default profile
    # ------------------------------------------------------------------

    assert (
        DEFAULT_LOCATION_PROFILE_ID
        in LOCATION_PROFILES
    )


# ============================================================================
# SELF TESTS
# ============================================================================

def _run_self_tests() -> None:
    """
    Run internal location profile tests.
    """

    print()
    print("=" * 70)
    print("LOCATION PROFILE TESTS")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Validate catalogue
    # ------------------------------------------------------------------

    validate_location_profiles()

    print(
        "Location profile catalogue: PASS"
    )

    # ------------------------------------------------------------------
    # City
    # ------------------------------------------------------------------

    city = get_location_profile(
        "city"
    )

    assert city.profile_id == "city"
    assert city.material_price_factor == 1.00

    # Use tolerance instead of exact floating-point comparison
    assert abs(
        city.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "City profile: PASS"
    )

    # ------------------------------------------------------------------
    # Big Town
    # ------------------------------------------------------------------

    big_town = get_location_profile(
        "big_town"
    )

    assert big_town.profile_id == "big_town"
    assert big_town.material_price_factor == 1.00

    assert abs(
        big_town.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "Big Town profile: PASS"
    )

    # ------------------------------------------------------------------
    # Small Town
    # ------------------------------------------------------------------

    small_town = get_location_profile(
        "small_town"
    )

    assert small_town.profile_id == "small_town"
    assert small_town.material_price_factor == 1.00

    assert abs(
        small_town.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "Small Town profile: PASS"
    )

    # ------------------------------------------------------------------
    # Growth Point
    # ------------------------------------------------------------------

    growth_point = get_location_profile(
        "growth_point"
    )

    assert (
        growth_point.profile_id
        == "growth_point"
    )

    assert (
        growth_point.material_price_factor
        == 1.00
    )

    assert abs(
        growth_point.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "Growth Point profile: PASS"
    )

    # ------------------------------------------------------------------
    # Rural / Farm
    # ------------------------------------------------------------------

    rural_farm = get_location_profile(
        "rural_farm"
    )

    assert (
        rural_farm.profile_id
        == "rural_farm"
    )

    assert (
        rural_farm.material_price_factor
        == 1.00
    )

    assert abs(
        rural_farm.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "Rural / Farm profile: PASS"
    )

    # ------------------------------------------------------------------
    # Legacy city_town
    # ------------------------------------------------------------------

    city_town = get_location_profile(
        "city_town"
    )

    assert (
        city_town.profile_id
        == "city_town"
    )

    assert (
        city_town.material_price_factor
        == 1.00
    )

    assert abs(
        city_town.adjustment_percentage - 0.00
    ) < 0.000001

    print(
        "Legacy city_town profile: PASS"
    )

    # ------------------------------------------------------------------
    # Available profiles
    # ------------------------------------------------------------------

    profiles = (
        get_available_location_profiles()
    )

    assert len(profiles) == 6

    profile_ids = {
        profile.profile_id
        for profile in profiles
    }

    assert profile_ids == {
        "city",
        "big_town",
        "small_town",
        "growth_point",
        "rural_farm",
        "city_town",
    }

    print(
        "Available profile list: PASS"
    )

    # ------------------------------------------------------------------
    # Invalid profile
    # ------------------------------------------------------------------

    try:

        get_location_profile(
            "invalid_profile"
        )

    except ValueError:

        pass

    else:

        raise AssertionError(
            "Invalid profile should raise ValueError."
        )

    print(
        "Invalid profile handling: PASS"
    )

    # ------------------------------------------------------------------
    # Compatibility property
    # ------------------------------------------------------------------

    test_profile = LocationPricingProfile(
        profile_id="test",
        name="Test",
        description="Test profile",
        material_price_factor=1.10,
    )

    # Floating-point-safe comparison
    assert abs(
        test_profile.adjustment_percentage - 10.00
    ) < 0.000001

    test_profile_negative = (
        LocationPricingProfile(
            profile_id="test_negative",
            name="Test Negative",
            description="Test profile",
            material_price_factor=0.95,
        )
    )

    # Floating-point-safe comparison
    assert abs(
        test_profile_negative.adjustment_percentage - (-5.00)
    ) < 0.000001

    print(
        "Backward compatibility property: PASS"
    )

    print("-" * 70)
    print(
        "ALL LOCATION PROFILE TESTS PASSED"
    )
    print("-" * 70)
    print()


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    _run_self_tests()