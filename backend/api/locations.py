"""
Location API for ZimBuild AI.

Provides endpoints for:
- Listing Zimbabwean provinces
- Listing districts within a province
- Retrieving the default settlement category for a district
- Validating province/district combinations

Location data is maintained in:
    backend/data/zimbabwe_locations.py

This module does not calculate prices or modify the estimation pipeline.
"""

from fastapi import APIRouter, HTTPException, Query

from data.zimbabwe_locations import (
    SETTLEMENT_CATEGORIES,
    get_provinces,
    get_districts,
    get_location_details,
    get_settlement_categories,
)


router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


# ---------------------------------------------------------
# GET /locations/provinces
# ---------------------------------------------------------

@router.get("/provinces")
def list_provinces():
    """
    Return all configured Zimbabwean provinces.
    """
    provinces = get_provinces()

    return {
        "success": True,
        "country": "Zimbabwe",
        "count": len(provinces),
        "provinces": provinces,
    }


# ---------------------------------------------------------
# GET /locations/districts?province=Masvingo
# ---------------------------------------------------------

@router.get("/districts")
def list_districts(
    province: str = Query(
        ...,
        min_length=1,
        description="The selected Zimbabwean province",
    ),
):
    """
    Return districts belonging to the selected province.
    """
    from data.zimbabwe_locations import get_canonical_province

    canonical_province = get_canonical_province(province)

    if canonical_province is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown province: {province}",
        )

    districts = get_districts(canonical_province)

    return {
        "success": True,
        "province": canonical_province,
        "count": len(districts),
        "districts": districts,
    }


# ---------------------------------------------------------
# GET /locations/categories
# ---------------------------------------------------------

@router.get("/categories")
def list_categories():
    """
    Return the three settlement categories used by ZimBuild AI.
    """
    categories = get_settlement_categories()

    return {
        "success": True,
        "count": len(categories),
        "categories": categories,
    }


# ---------------------------------------------------------
# GET /locations/category
#     ?province=Masvingo&district=Bikita
# ---------------------------------------------------------

@router.get("/category")
def get_category(
    province: str = Query(
        ...,
        min_length=1,
        description="The selected Zimbabwean province",
    ),
    district: str = Query(
        ...,
        min_length=1,
        description="The selected district",
    ),
):
    """
    Return the default settlement category for a district.

    The district must belong to the selected province.
    """
    details = get_location_details(province, district)

    if details is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Invalid province/district combination: "
                f"{province} / {district}"
            ),
        )

    category_id = details["settlement_category"]

    category_details = SETTLEMENT_CATEGORIES.get(category_id)

    if category_details is None:
        raise HTTPException(
            status_code=500,
            detail="The district has an invalid settlement category.",
        )

    return {
        "success": True,
        **details,
        "category": category_details,
    }


# ---------------------------------------------------------
# GET /locations/validate
#     ?province=Masvingo&district=Bikita
# ---------------------------------------------------------

@router.get("/validate")
def validate_location(
    province: str = Query(
        ...,
        min_length=1,
        description="The selected Zimbabwean province",
    ),
    district: str = Query(
        ...,
        min_length=1,
        description="The selected district",
    ),
):
    """
    Validate a province/district combination and return its details.
    """
    details = get_location_details(province, district)

    if details is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Invalid province/district combination: "
                f"{province} / {district}"
            ),
        )

    return {
        "success": True,
        "valid": True,
        **details,
    }
