from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from pydantic import BaseModel, Field

from backend.services.plan_preprocessor import (
    preprocess_raster_plan,
)

from backend.services.plan_service import (
    generate_stored_filename,
    get_upload_path,
    validate_file_size,
)

from backend.services.plan_validator import (
    validate_plan_file,
)

from backend.services.phase8_service import (
    analyse_plan,
)

from backend.services.scale_calibration import (
    load_calibration,
    save_calibration,
)


# ============================================================
# SCALE CALIBRATION REQUEST
# ============================================================

class ScaleCalibrationRequest(BaseModel):
    """
    Data supplied by the user to establish
    the scale of an architectural plan.
    """

    pixel_distance: float = Field(
        ...,
        gt=0,
        description=(
            "Known distance measured in image pixels."
        ),
    )

    known_distance_m: float = Field(
        ...,
        gt=0,
        description=(
            "The corresponding real-world "
            "distance in metres."
        ),
    )


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/plans",
    tags=["Plans"],
)


# ============================================================
# PLAN SERVICE INFORMATION
# ============================================================

@router.get("/")
def plans_info():
    """
    Basic information about the plan-processing API.
    """

    return {
        "service": "Plan Processing",
        "status": "available",
    }


# ============================================================
# UPLOAD PLAN
# ============================================================

@router.post("/upload")
async def upload_plan(
    file: UploadFile = File(...),
):
    """
    Upload an architectural plan.

    The uploaded file is validated and stored locally.
    """

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    original_filename = Path(
        file.filename
    ).name

    try:

        stored_filename = (
            generate_stored_filename(
                original_filename
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    contents = await file.read()

    try:

        validate_file_size(
            len(contents)
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc

    upload_path = get_upload_path(
        stored_filename
    )

    upload_path.write_bytes(
        contents
    )

    return {

        "status": "uploaded",

        "original_filename": (
            original_filename
        ),

        "stored_filename": (
            stored_filename
        ),

        "file_extension": (
            upload_path.suffix.lower()
        ),

        "file_size_bytes": (
            len(contents)
        ),

        "file_size_mb": round(
            len(contents) /
            (1024 * 1024),
            4,
        ),
    }


# ============================================================
# VALIDATE UPLOADED PLAN
# ============================================================

@router.get(
    "/validate/{stored_filename}"
)
def validate_uploaded_plan(
    stored_filename: str,
):
    """
    Validate an already uploaded
    architectural plan.
    """

    try:

        result = validate_plan_file(
            stored_filename
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return result


# ============================================================
# PREPROCESS PLAN
# ============================================================

@router.post(
    "/preprocess/{stored_filename}"
)
def preprocess_uploaded_plan(
    stored_filename: str,
):
    """
    Preprocess a raster architectural plan.

    PNG/JPG/JPEG files are normalised
    into PNG while preserving their
    original dimensions.
    """

    try:

        result = preprocess_raster_plan(
            stored_filename
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return result


# ============================================================
# PHASE 8 — WALL ANALYSIS
# ============================================================

@router.post(
    "/analyse/{processed_filename}"
)
def analyse_processed_plan(
    processed_filename: str,
):
    """
    Analyse a processed architectural plan
    using the Phase 8 wall-segmentation and
    wall-axis measurement pipeline.

    If a scale calibration already exists for
    this plan, it is automatically loaded and
    used to convert wall lengths into metres.
    """

    # --------------------------------------------------------
    # Resolve filename safely
    # --------------------------------------------------------

    filename = Path(
        processed_filename
    ).name

    if filename != processed_filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid processed filename.",
        )

    # --------------------------------------------------------
    # Processed-plan directory
    # --------------------------------------------------------

    processed_dir = (
        Path(__file__).resolve().parents[1]
        / "processed_plans"
    )

    processed_path = (
        processed_dir / filename
    )

    # --------------------------------------------------------
    # Check file exists
    # --------------------------------------------------------

    if not processed_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Processed plan "
                f"'{filename}' was not found."
            ),
        )

    if not processed_path.is_file():

        raise HTTPException(
            status_code=400,
            detail=(
                "The selected processed "
                "plan is not a file."
            ),
        )

    # --------------------------------------------------------
    # Load existing calibration if available
    # --------------------------------------------------------

    try:

        calibration = load_calibration(
            filename
        )

        pixels_per_metre = None

        if calibration is not None:

            pixels_per_metre = (
                calibration[
                    "pixels_per_metre"
                ]
            )

        # ----------------------------------------------------
        # Phase 8 analysis
        # ----------------------------------------------------

        result = analyse_plan(
            processed_path,
            pixels_per_metre=pixels_per_metre,
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Phase 8 plan analysis failed: "
                f"{exc}"
            ),
        ) from exc

    return result


# ============================================================
# PHASE 13.2 — SCALE CALIBRATION
# ============================================================

@router.post(
    "/calibrate/{processed_filename}"
)
def calibrate_processed_plan(
    processed_filename: str,
    calibration_request: ScaleCalibrationRequest,
):
    """
    Establish the real-world scale of a
    processed architectural plan.

    The user supplies:

    1. A known pixel distance.
    2. The corresponding real-world distance
       in metres.

    The API calculates pixels per metre,
    saves the calibration, and immediately
    re-runs Phase 8 analysis using the
    calibrated scale.
    """

    # --------------------------------------------------------
    # Resolve filename safely
    # --------------------------------------------------------

    filename = Path(
        processed_filename
    ).name

    if filename != processed_filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid processed filename.",
        )

    # --------------------------------------------------------
    # Processed-plan directory
    # --------------------------------------------------------

    processed_dir = (
        Path(__file__).resolve().parents[1]
        / "processed_plans"
    )

    processed_path = (
        processed_dir / filename
    )

    # --------------------------------------------------------
    # Check file exists
    # --------------------------------------------------------

    if not processed_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Processed plan "
                f"'{filename}' was not found."
            ),
        )

    if not processed_path.is_file():

        raise HTTPException(
            status_code=400,
            detail=(
                "The selected processed "
                "plan is not a file."
            ),
        )

    # --------------------------------------------------------
    # Save calibration
    # --------------------------------------------------------

    try:

        calibration = save_calibration(
            processed_filename=filename,
            pixel_distance=(
                calibration_request.pixel_distance
            ),
            known_distance_m=(
                calibration_request.known_distance_m
            ),
        )

        # ----------------------------------------------------
        # Immediately analyse using calibrated scale
        # ----------------------------------------------------

        result = analyse_plan(
            processed_path,
            pixels_per_metre=(
                calibration[
                    "pixels_per_metre"
                ]
            ),
        )

        # Add calibration information
        # to the API response.

        result["calibration"] = calibration

        return result

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Scale calibration failed: "
                f"{exc}"
            ),
        ) from exc