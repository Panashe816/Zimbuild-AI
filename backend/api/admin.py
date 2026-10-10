from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.dependencies import get_admin_claims
from backend.database import engine
from backend.models import Estimate, Plan, User

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/dashboard")
def admin_dashboard(_: dict[str, Any] = Depends(get_admin_claims)):
    """Return administrator-only aggregate statistics and recent projects."""
    with Session(engine) as db:
        total_plans = db.query(func.count(Plan.id)).scalar() or 0
        total_estimates = db.query(func.count(Estimate.id)).scalar() or 0
        total_users = db.query(func.count(User.id)).scalar() or 0

        rows = (
            db.query(Plan, Estimate, User)
            .outerjoin(Estimate, Estimate.plan_id == Plan.id)
            .outerjoin(User, User.id == Plan.user_id)
            .order_by(Estimate.created_at.desc().nullslast(), Plan.created_at.desc())
            .limit(100)
            .all()
        )

        projects = []
        seen_estimates = set()
        for plan, estimate, user in rows:
            key = estimate.id if estimate else f"plan-{plan.id}"
            if key in seen_estimates:
                continue
            seen_estimates.add(key)
            result = estimate.results if estimate and isinstance(estimate.results, dict) else {}
            project = result.get("project") or {}
            totals = result.get("totals") or {}
            projects.append({
                "plan_id": plan.id,
                "estimate_id": estimate.id if estimate else None,
                "project_name": project.get("project_name") or plan.original_filename,
                "location": project.get("location") or "—",
                "original_filename": plan.original_filename,
                "status": plan.status,
                "user_email": user.email if user else "Unassigned / legacy record",
                "user_name": user.name if user else "—",
                "total_cost": estimate.total_cost if estimate and estimate.total_cost is not None else totals.get("grand_total"),
                "currency": estimate.currency if estimate else project.get("currency", "USD"),
                "created_at": (estimate.created_at if estimate else plan.created_at).isoformat(),
            })

        return {
            "total_plans": total_plans,
            "total_estimates": total_estimates,
            "total_users": total_users,
            "recent_projects": projects,
        }
