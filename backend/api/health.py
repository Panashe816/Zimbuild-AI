from fastapi import APIRouter


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
def health_check():
    """
    Basic API health-check endpoint.
    """
    return {
        "status": "ok",
        "service": "ZimBuild AI API",
    }