from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from statistics import mean, median
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.dependencies import get_admin_claims
from backend.database import engine
from backend.models import Estimate, Plan, User

router = APIRouter(prefix="/admin", tags=["Administration"])


def _estimate_records(db: Session):
    return (
        db.query(Plan, Estimate, User)
        .join(Estimate, Estimate.plan_id == Plan.id)
        .outerjoin(User, User.id == Plan.user_id)
        .order_by(Estimate.created_at.desc())
        .all()
    )


def _project_record(plan: Plan, estimate: Estimate, user: User | None) -> dict[str, Any]:
    result = estimate.results if isinstance(estimate.results, dict) else {}
    project = result.get("project") or {}
    totals = result.get("totals") or {}
    analysis = result.get("analysis") or {}
    return {
        "plan_id": plan.id,
        "estimate_id": estimate.id,
        "project_name": project.get("project_name") or plan.original_filename,
        "location": project.get("location") or "—",
        "original_filename": plan.original_filename,
        "status": plan.status,
        "user_email": user.email if user else "Unassigned / legacy record",
        "user_name": user.name if user else "—",
        "total_cost": estimate.total_cost if estimate.total_cost is not None else totals.get("grand_total"),
        "currency": estimate.currency or project.get("currency", "USD"),
        "created_at": (estimate.created_at or plan.created_at).isoformat(),
        "floor_area_m2": analysis.get("floor_area_m2"),
        "totals": totals,
        "result": result,
    }


def _build_reports(db: Session) -> dict[str, Any]:
    records = _estimate_records(db)
    projects = [_project_record(plan, estimate, user) for plan, estimate, user in records]
    currencies = defaultdict(list)
    locations = defaultdict(lambda: {"projects": 0, "costs": [], "currency": "USD"})
    districts = defaultdict(lambda: {"projects": 0, "costs": [], "currency": "USD"})
    material_history = defaultdict(list)
    cost_components = {"Materials": [], "Labour": [], "Transport": []}

    for project in projects:
        currency = project["currency"] or "USD"
        cost = project["total_cost"]
        if cost is not None:
            currencies[currency].append(float(cost))
        location = str(project["location"] or "—")
        if location == "—":
            province, district = "Not recorded", "Not recorded"
        else:
            parts = [part.strip() for part in location.split(",")]
            district = parts[0] if parts else "Not recorded"
            province = parts[1] if len(parts) > 1 else "Not recorded"
        locations[province]["projects"] += 1
        locations[province]["currency"] = currency
        districts[f"{district}, {province}"]["projects"] += 1
        districts[f"{district}, {province}"]["currency"] = currency
        if cost is not None:
            locations[province]["costs"].append(float(cost))
            districts[f"{district}, {province}"]["costs"].append(float(cost))

        totals = project["totals"] if isinstance(project["totals"], dict) else {}
        for label, key in (("Materials", "materials"), ("Labour", "labour"), ("Transport", "transport")):
            value = totals.get(key)
            if value is not None:
                cost_components[label].append(float(value))

        result = project["result"]
        phase12 = result.get("phase12") or {}
        items = phase12.get("items") or []
        if isinstance(items, dict):
            items = list(items.values())
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("description") or item.get("material") or item.get("name") or item.get("item_name") or "").strip()
            if not name:
                continue
            rate = item.get("rate", item.get("unit_rate", item.get("unit_price", item.get("price"))))
            if rate is None:
                continue
            try:
                material_history[name].append({
                    "rate": float(rate),
                    "date": project["created_at"][:10],
                    "currency": currency,
                    "unit": item.get("unit") or item.get("unit_of_measure") or "",
                })
            except (TypeError, ValueError):
                continue

    total_costs = [float(p["total_cost"]) for p in projects if p["total_cost"] is not None]
    cost_by_currency = []
    for currency, values in sorted(currencies.items()):
        cost_by_currency.append({
            "currency": currency,
            "project_count": len(values),
            "average_cost": round(mean(values), 2),
            "median_cost": round(median(values), 2),
            "total_cost": round(sum(values), 2),
        })

    location_rows = [
        {
            "location": name,
            "project_count": data["projects"],
            "average_cost": round(mean(data["costs"]), 2) if data["costs"] else None,
            "currency": data["currency"],
        }
        for name, data in locations.items()
    ]
    district_rows = [
        {
            "location": name,
            "project_count": data["projects"],
            "average_cost": round(mean(data["costs"]), 2) if data["costs"] else None,
            "currency": data["currency"],
        }
        for name, data in districts.items()
    ]
    location_rows.sort(key=lambda row: row["project_count"], reverse=True)
    district_rows.sort(key=lambda row: row["project_count"], reverse=True)

    material_rows = []
    for name, entries in material_history.items():
        entries.sort(key=lambda entry: entry["date"])
        first, last = entries[0], entries[-1]
        change = None
        if first["rate"] != 0:
            change = round(((last["rate"] - first["rate"]) / first["rate"]) * 100, 2)
        material_rows.append({
            "material": name,
            "unit": last["unit"],
            "currency": last["currency"],
            "observations": len(entries),
            "latest_rate": last["rate"],
            "first_rate": first["rate"],
            "change_percent": change,
            "history": entries,
        })
    material_rows.sort(key=lambda row: row["material"].lower())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_plans": db.query(func.count(Plan.id)).scalar() or 0,
            "total_estimates": db.query(func.count(Estimate.id)).scalar() or 0,
            "total_users": db.query(func.count(User.id)).scalar() or 0,
            "completed_estimates": len(projects),
            "average_cost_by_currency": cost_by_currency,
            "average_cost": round(mean(total_costs), 2) if total_costs else None,
            "currency": cost_by_currency[0]["currency"] if len(cost_by_currency) == 1 else None,
        },
        "location_report": {"provinces": location_rows, "districts": district_rows},
        "cost_report": {
            "cost_by_currency": cost_by_currency,
            "cost_components": [
                {"component": label, "average": round(mean(values), 2) if values else None, "currency": None}
                for label, values in cost_components.items()
            ],
        },
        "material_report": {
            "items": material_rows,
            "note": "Price observations are extracted from saved estimates. A material price history is available only where saved BoQ records include comparable unit rates.",
        },
        "recent_projects": [
            {key: value for key, value in project.items() if key not in {"totals", "result", "floor_area_m2"}}
            for project in sorted(projects, key=lambda item: item["created_at"], reverse=True)[:100]
        ],
    }


@router.get("/dashboard")
def admin_dashboard(_: dict[str, Any] = Depends(get_admin_claims)):
    """Return administrator-only summary, reports and recent project records."""
    with Session(engine) as db:
        return _build_reports(db)


@router.get("/reports/{report_key}/pdf")
def export_admin_report_pdf(
    report_key: str,
    _: dict[str, Any] = Depends(get_admin_claims),
):
    """Export one of the three administrator analytics reports as a PDF."""
    report_titles = {
        "locations": "Construction Activity by Location",
        "costs": "Building Cost and BoQ Analysis",
        "materials": "Material Price Observations",
    }
    if report_key not in report_titles:
        raise HTTPException(status_code=404, detail="Unknown report type.")

    with Session(engine) as db:
        data = _build_reports(db)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=15 * mm,
        leftMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ZimBuild AI", styles["Title"]),
        Paragraph(report_titles[report_key], styles["Heading2"]),
        Paragraph(f"Generated: {data['generated_at'][:19].replace('T', ' ')} UTC", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]

    if report_key == "locations":
        rows = [["Province", "Projects", "Average estimated cost"]]
        for row in data["location_report"]["provinces"]:
            average = f"{row['currency']} {row['average_cost']:,.2f}" if row["average_cost"] is not None else "—"
            rows.append([row["location"], str(row["project_count"]), average])
        if len(rows) == 1:
            rows.append(["No recorded locations", "0", "—"])
    elif report_key == "costs":
        rows = [["Currency", "Estimates", "Average cost", "Median cost", "Total estimated cost"]]
        for row in data["cost_report"]["cost_by_currency"]:
            rows.append([
                row["currency"], str(row["project_count"]),
                f"{row['average_cost']:,.2f}", f"{row['median_cost']:,.2f}",
                f"{row['total_cost']:,.2f}",
            ])
        if len(rows) == 1:
            rows.append(["—", "0", "—", "—", "—"])
    else:
        rows = [["Material", "Unit", "Currency", "First rate", "Latest rate", "Change", "Observations"]]
        for row in data["material_report"]["items"]:
            change = f"{row['change_percent']:.2f}%" if row["change_percent"] is not None else "Insufficient history"
            rows.append([
                row["material"], row["unit"], row["currency"],
                f"{row['first_rate']:,.2f}", f"{row['latest_rate']:,.2f}",
                change, str(row["observations"]),
            ])
        if len(rows) == 1:
            rows.append(["No rate observations", "—", "—", "—", "—", "—", "0"])

    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3ed")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "Report values are calculated from saved ZimBuild AI records. Location and price insights reflect recorded platform activity, not a complete national construction survey. Material price changes are shown only when saved estimates contain comparable rate observations.",
        styles["BodyText"],
    ))
    document.build(story)
    buffer.seek(0)
    filename = f"zimbuild_{report_key}_report.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
