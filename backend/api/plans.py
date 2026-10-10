from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Plan


# ============================================================
# DIRECTORIES
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIR = PROJECT_ROOT / "backend" / "uploads"
PROCESSED_DIR = PROJECT_ROOT / "backend" / "processed_plans"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# SETTINGS
# ============================================================

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
}


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
    Information about the plan upload service.

    This endpoint belongs to the new AI Visualiser pipeline.
    """

    return {
        "service": "ZimBuild AI Plan Upload",
        "status": "available",
        "pipeline": "AI Visualiser",
        "supported_formats": sorted(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE_MB,
    }


# ============================================================
# UPLOAD PLAN
# ============================================================

@router.post("/upload")
async def upload_plan(
    file: UploadFile = File(...),
):
    """
    Upload an architectural floor plan.

    The file is stored temporarily so that it can subsequently
    be processed by the new AI Visualiser pipeline.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. "
                "Please upload a PNG, JPG, or JPEG architectural plan."
            ),
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"The uploaded file is too large. "
                f"Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
            ),
        )

    # Generate a unique filename so multiple users/uploads
    # do not overwrite one another.
    stored_filename = (
        f"{uuid4().hex}{extension}"
    )

    upload_path = UPLOAD_DIR / stored_filename

    try:
        upload_path.write_bytes(contents)

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to store the uploaded plan.",
        ) from exc

    # Persist the plan record in PostgreSQL while keeping the existing
    # upload path and frontend response fields unchanged.
    try:
        with Session(engine) as db:
            plan_record = Plan(
                original_filename=original_filename,
                stored_filename=stored_filename,
                status="uploaded",
            )
            db.add(plan_record)
            db.commit()
            db.refresh(plan_record)
            plan_id = plan_record.id
    except Exception as exc:
        try:
            upload_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status_code=500,
            detail="The plan file was received but could not be saved to the database.",
        ) from exc

    return {
        "status": "uploaded",
        "plan_id": plan_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_extension": extension,
        "file_size_bytes": len(contents),
        "file_size_mb": round(
            len(contents) / (1024 * 1024),
            4,
        ),
    }


# ============================================================
# PREPARE PLAN FOR NEW AI VISUALISER
# ============================================================

@router.post("/preprocess/{stored_filename}")
def preprocess_uploaded_plan(
    stored_filename: str,
):
    """
    Prepare an uploaded architectural plan for the new
    AI Visualiser pipeline.

    No old Phase 1–13 processing is used here.

    The current AI Visualiser can analyse the original raster
    image directly, so this step safely copies the uploaded
    raster image into the processed-plans directory.

    The frontend continues using the existing
    /plans/preprocess/{filename} workflow.
    """

    filename = Path(stored_filename).name

    # Prevent directory traversal.
    if filename != stored_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    source_path = UPLOAD_DIR / filename

    if not source_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Uploaded plan '{filename}' was not found."
            ),
        )

    if not source_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="The selected uploaded plan is not a file.",
        )

    extension = source_path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported architectural plan format.",
        )

    # Keep the same filename so the frontend can pass the
    # returned processed_filename directly to /estimation/full.
    processed_path = PROCESSED_DIR / filename

    try:
        processed_path.write_bytes(
            source_path.read_bytes()
        )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to prepare the plan for AI analysis.",
        ) from exc

    return {
        "status": "processed",
        "original_filename": filename,
        "processed_filename": filename,
        "processed_path": str(processed_path),
        "file_extension": extension,
        "message": (
            "Plan prepared successfully for the new "
            "AI Visualiser pipeline."
        ),
    }