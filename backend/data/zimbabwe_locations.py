"""
Zimbabwe location catalogue for ZimBuild AI.

Purpose:
    Map Zimbabwean provinces and districts to the application's
    existing settlement/pricing categories.

Categories:
    city_big_town
    small_town
    growth_point_rural_farm

IMPORTANT:
    These are application defaults, not official classifications
    of every settlement within a district.

    Districts may contain both urban and rural areas. Since this
    version uses province and district only, each district has one
    default category for estimating location-sensitive costs.

    Keep pricing rates and pricing profile IDs in the existing
    location-pricing module, not in this file.
"""

from typing import Any


# ---------------------------------------------------------
# EXISTING APPLICATION CATEGORY IDS
# ---------------------------------------------------------

CITY_BIG_TOWN = "city_big_town"
SMALL_TOWN = "small_town"
GROWTH_POINT_RURAL_FARM = "growth_point_rural_farm"


SETTLEMENT_CATEGORIES = {
    CITY_BIG_TOWN: {
        "id": CITY_BIG_TOWN,
        "label": "Cities / Big Towns",
    },
    SMALL_TOWN: {
        "id": SMALL_TOWN,
        "label": "Small Towns",
    },
    GROWTH_POINT_RURAL_FARM: {
        "id": GROWTH_POINT_RURAL_FARM,
        "label": "Growth Points / Rural Areas / Farms",
    },
}


# ---------------------------------------------------------
# PROVINCES AND DISTRICTS
#
# Each district has a default category used by ZimBuild AI.
# Review these defaults against your existing pricing profiles
# before applying them to production estimates.
# ---------------------------------------------------------

ZIMBABWE_LOCATIONS: dict[str, dict[str, Any]] = {
    "Bulawayo": {
        "districts": {
            "Bulawayo": CITY_BIG_TOWN,
        }
    },

    "Harare Metropolitan": {
        "districts": {
            "Harare": CITY_BIG_TOWN,
            "Chitungwiza": SMALL_TOWN,
            "Epworth": SMALL_TOWN,
        }
    },

    "Manicaland": {
        "districts": {
            "Buhera": GROWTH_POINT_RURAL_FARM,
            "Chimanimani": SMALL_TOWN,
            "Chipinge": SMALL_TOWN,
            "Makoni": GROWTH_POINT_RURAL_FARM,
            "Mutare": CITY_BIG_TOWN,
            "Mutasa": GROWTH_POINT_RURAL_FARM,
            "Nyanga": SMALL_TOWN,
        }
    },

    "Mashonaland Central": {
        "districts": {
            "Bindura": SMALL_TOWN,
            "Guruve": GROWTH_POINT_RURAL_FARM,
            "Mazowe": GROWTH_POINT_RURAL_FARM,
            "Mbire": GROWTH_POINT_RURAL_FARM,
            "Mount Darwin": GROWTH_POINT_RURAL_FARM,
            "Muzarabani": GROWTH_POINT_RURAL_FARM,
            "Rushinga": GROWTH_POINT_RURAL_FARM,
            "Shamva": GROWTH_POINT_RURAL_FARM,
        }
    },

    "Mashonaland East": {
        "districts": {
            "Chikomba": GROWTH_POINT_RURAL_FARM,
            "Goromonzi": GROWTH_POINT_RURAL_FARM,
            "Hwedza": GROWTH_POINT_RURAL_FARM,
            "Marondera": SMALL_TOWN,
            "Mudzi": GROWTH_POINT_RURAL_FARM,
            "Murehwa": GROWTH_POINT_RURAL_FARM,
            "Mutoko": GROWTH_POINT_RURAL_FARM,
            "Ruwa": SMALL_TOWN,
            "Seke": GROWTH_POINT_RURAL_FARM,
            "Uzumba-Maramba-Pfungwe": GROWTH_POINT_RURAL_FARM,
            "Wedza": GROWTH_POINT_RURAL_FARM,
        }
    },

    "Mashonaland West": {
        "districts": {
            "Chegutu": SMALL_TOWN,
            "Chinhoyi": SMALL_TOWN,
            "Hurungwe": GROWTH_POINT_RURAL_FARM,
            "Kadoma": SMALL_TOWN,
            "Kariba": SMALL_TOWN,
            "Karoi": SMALL_TOWN,
            "Makonde": GROWTH_POINT_RURAL_FARM,
            "Mhondoro-Ngezi": GROWTH_POINT_RURAL_FARM,
            "Norton": SMALL_TOWN,
            "Sanyati": GROWTH_POINT_RURAL_FARM,
            "Zvimba": GROWTH_POINT_RURAL_FARM,
        }
    },

    "Masvingo": {
        "districts": {
            "Bikita": GROWTH_POINT_RURAL_FARM,
            "Chiredzi": SMALL_TOWN,
            "Chivi": GROWTH_POINT_RURAL_FARM,
            "Gutu": GROWTH_POINT_RURAL_FARM,
            "Masvingo": CITY_BIG_TOWN,
            "Mwenezi": GROWTH_POINT_RURAL_FARM,
            "Zaka": GROWTH_POINT_RURAL_FARM,
        }
    },

    "Matabeleland North": {
        "districts": {
            "Binga": GROWTH_POINT_RURAL_FARM,
            "Bubi": GROWTH_POINT_RURAL_FARM,
            "Hwange": SMALL_TOWN,
            "Lupane": GROWTH_POINT_RURAL_FARM,
            "Nkayi": GROWTH_POINT_RURAL_FARM,
            "Tsholotsho": GROWTH_POINT_RURAL_FARM,
            "Umguza": GROWTH_POINT_RURAL_FARM,
            "Victoria Falls": SMALL_TOWN,
        }
    },

    "Matabeleland South": {
        "districts": {
            "Beitbridge": SMALL_TOWN,
            "Bulilima": GROWTH_POINT_RURAL_FARM,
            "Gwanda": SMALL_TOWN,
            "Insiza": GROWTH_POINT_RURAL_FARM,
            "Mangwe": GROWTH_POINT_RURAL_FARM,
            "Matobo": GROWTH_POINT_RURAL_FARM,
            "Umzingwane": GROWTH_POINT_RURAL_FARM,
        }
    },

    "Midlands": {
        "districts": {
            "Chirumhanzu": GROWTH_POINT_RURAL_FARM,
            "Gokwe North": GROWTH_POINT_RURAL_FARM,
            "Gokwe South": GROWTH_POINT_RURAL_FARM,
            "Gweru": CITY_BIG_TOWN,
            "Gweru Rural": GROWTH_POINT_RURAL_FARM,
            "Gweru Urban": CITY_BIG_TOWN,
            "Kwekwe": SMALL_TOWN,
            "Mberengwa": GROWTH_POINT_RURAL_FARM,
            "Shurugwi": SMALL_TOWN,
            "Zvishavane": SMALL_TOWN,
        }
    },
}


# ---------------------------------------------------------
# NAME ALIASES
#
# Allows common alternative spellings to resolve to a
# canonical province or district name.
# ---------------------------------------------------------

PROVINCE_ALIASES = {
    "Harare": "Harare Metropolitan",
    "Harare Province": "Harare Metropolitan",
    "Bulawayo Metropolitan": "Bulawayo",
    "Bulawayo Metropolitan Province": "Bulawayo",
    "Matabeleland North Province": "Matabeleland North",
    "Matabeleland South Province": "Matabeleland South",
    "Mashonaland Central Province": "Mashonaland Central",
    "Mashonaland East Province": "Mashonaland East",
    "Mashonaland West Province": "Mashonaland West",
    "Manicaland Province": "Manicaland",
    "Masvingo Province": "Masvingo",
    "Midlands Province": "Midlands",
}

DISTRICT_ALIASES = {
    "UMP": "Uzumba-Maramba-Pfungwe",
    "Uzumba Maramba Pfungwe": "Uzumba-Maramba-Pfungwe",
    "Murehwa District": "Murehwa",
    "Mt Darwin": "Mount Darwin",
    "Victoria Falls District": "Victoria Falls",
    "Gokwe North District": "Gokwe North",
    "Gokwe South District": "Gokwe South",
    "Zvishawane": "Zvishavane",
}


# ---------------------------------------------------------
# PUBLIC HELPER FUNCTIONS
# ---------------------------------------------------------

def _normalise(value: str) -> str:
    """Normalise a name for case-insensitive matching."""
    return " ".join(value.strip().casefold().split())


def get_provinces() -> list[str]:
    """Return the configured Zimbabwean provinces."""
    return sorted(ZIMBABWE_LOCATIONS.keys())


def get_districts(province: str) -> list[str]:
    """Return districts for a province, or an empty list if unknown."""
    canonical_province = get_canonical_province(province)

    if canonical_province is None:
        return []

    return sorted(
        ZIMBABWE_LOCATIONS[canonical_province]["districts"].keys()
    )


def get_canonical_province(province: str) -> str | None:
    """Resolve a province name or supported alias."""
    if not isinstance(province, str) or not province.strip():
        return None

    lookup = {
        _normalise(name): name
        for name in ZIMBABWE_LOCATIONS
    }

    for alias, canonical in PROVINCE_ALIASES.items():
        lookup[_normalise(alias)] = canonical

    return lookup.get(_normalise(province))


def get_canonical_district(district: str) -> str | None:
    """Resolve a district name or supported alias."""
    if not isinstance(district, str) or not district.strip():
        return None

    lookup = {
        _normalise(name): name
        for location_data in ZIMBABWE_LOCATIONS.values()
        for name in location_data["districts"]
    }

    for alias, canonical in DISTRICT_ALIASES.items():
        lookup[_normalise(alias)] = canonical

    return lookup.get(_normalise(district))


def get_district_category(
    province: str,
    district: str,
) -> str | None:
    """
    Return the default category for a district within a province.

    Returns None when the province/district combination is unknown.
    """
    canonical_province = get_canonical_province(province)

    if canonical_province is None:
        return None

    districts = ZIMBABWE_LOCATIONS[canonical_province]["districts"]

    # Resolve the district only against the selected province.
    district_lookup = {
        _normalise(name): name
        for name in districts
    }

    for alias, canonical in DISTRICT_ALIASES.items():
        if canonical in districts:
            district_lookup[_normalise(alias)] = canonical

    canonical_district = district_lookup.get(_normalise(district))

    if canonical_district is None:
        return None

    return districts[canonical_district]


def get_location_details(
    province: str,
    district: str,
) -> dict[str, str] | None:
    """Return canonical province, district and default category."""
    canonical_province = get_canonical_province(province)

    if canonical_province is None:
        return None

    category = get_district_category(canonical_province, district)

    if category is None:
        return None

    districts = ZIMBABWE_LOCATIONS[canonical_province]["districts"]
    district_lookup = {
        _normalise(name): name
        for name in districts
    }

    for alias, canonical in DISTRICT_ALIASES.items():
        if canonical in districts:
            district_lookup[_normalise(alias)] = canonical

    canonical_district = district_lookup.get(_normalise(district))

    if canonical_district is None:
        return None

    return {
        "province": canonical_province,
        "district": canonical_district,
        "settlement_category": category,
        "category_label": SETTLEMENT_CATEGORIES[category]["label"],
    }


def is_valid_location(province: str, district: str) -> bool:
    """Check whether a district belongs to the selected province."""
    return get_location_details(province, district) is not None


def get_settlement_categories() -> list[dict[str, str]]:
    """Return the three application settlement categories."""
    return list(SETTLEMENT_CATEGORIES.values())
