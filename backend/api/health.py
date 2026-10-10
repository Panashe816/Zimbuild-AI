
from fastapi import APIRouter, HTTPException

from backend.database import test_database_connection


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
def health_check():
    """Check whether the API is running."""
    return {
        "status": "ok",
        "service": "ZimBuild AI API",
    }


@router.get("/database")
def database_health_check():
    """Check whether PostgreSQL is reachable."""
    try:
        connected = test_database_connection()

        if not connected:
            raise HTTPException(
                status_code=503,
                detail="Database connection failed.",
            )

        return {
            "status": "ok",
            "database": "connected",
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database connection failed. "
                "Check the backend environment and database configuration."
            ),
        ) from None
