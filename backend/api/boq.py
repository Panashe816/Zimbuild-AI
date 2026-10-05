from fastapi import APIRouter


router = APIRouter(
    prefix="/boq",
    tags=["Bill of Quantities"],
)


@router.get("/")
def boq_info():
    """
    Basic information about the BoQ API.
    """
    return {
        "service": "Bill of Quantities",
        "status": "available",
    }