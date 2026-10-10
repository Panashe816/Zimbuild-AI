from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from backend.api.dependencies import get_token_claims
from backend.database import engine
from backend.models import Estimate, Plan, User

router = APIRouter(prefix="/boq", tags=["Bill of Quantities"])


@router.get("/")
def boq_info():
    return {"service": "Bill of Quantities", "status": "available"}


def _money(value: Any, currency: str = "USD") -> str:
    try:
        return f"{currency} {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"


@router.get("/{estimate_id}/pdf")
def download_boq_pdf(
    estimate_id: int,
    claims: dict[str, Any] = Depends(get_token_claims),
):
    """Create a PDF BoQ for an estimate owned by the signed-in user or admin."""
    with Session(engine) as db:
        record = (
            db.query(Estimate, Plan, User)
            .join(Plan, Estimate.plan_id == Plan.id)
            .outerjoin(User, Plan.user_id == User.id)
            .filter(Estimate.id == estimate_id)
            .one_or_none()
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Estimate not found.")

        estimate, plan, owner = record
        is_admin = claims.get("role") == "admin"
        if not is_admin:
            if claims.get("role") != "user" or owner is None or owner.google_id != str(claims.get("sub")):
                raise HTTPException(status_code=404, detail="Estimate not found.")

        result = estimate.results if isinstance(estimate.results, dict) else {}
        project = result.get("project") or {}
        phase12 = result.get("phase12") or {}
        phase11 = result.get("phase11") or {}
        totals = result.get("totals") or {}
        items = phase12.get("items") or []
        stages = phase11.get("stages") or []
        project_name = str(project.get("project_name") or plan.original_filename or f"Project {plan.id}")
        location = str(project.get("location") or "Not specified")
        currency = str(estimate.currency or project.get("currency") or "USD")
        total_cost = estimate.total_cost if estimate.total_cost is not None else totals.get("grand_total", 0)
        material_subtotal = phase12.get("material_subtotal", totals.get("materials", 0))
        labour_total = phase12.get("labour_total", totals.get("labour", 0))
        transport_total = phase12.get("transport_total", totals.get("transport", 0))

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=14 * mm,
            leftMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=f"Bill of Quantities - {project_name}",
            author="ZimBuild AI",
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("ZimBuild AI", styles["Title"]),
            Paragraph("Bill of Quantities and Construction Cost Estimate", styles["Heading2"]),
            Spacer(1, 4 * mm),
            Paragraph(f"<b>Project:</b> {escape(project_name)}", styles["Normal"]),
            Paragraph(f"<b>Location:</b> {escape(location)}", styles["Normal"]),
            Paragraph(f"<b>Plan file:</b> {escape(plan.original_filename)}", styles["Normal"]),
            Paragraph(f"<b>Estimate reference:</b> {estimate.id}", styles["Normal"]),
            Spacer(1, 5 * mm),
            Paragraph("Priced bill of quantities", styles["Heading2"]),
        ]

        table_data = [["No.", "Stage", "Description", "Quantity", "Unit", "Rate", "Amount"]]
        for index, item in enumerate(items, start=1):
            table_data.append([
                str(item.get("item_number") or index),
                str(item.get("stage_name") or ""),
                str(item.get("description") or item.get("material_name") or ""),
                f"{float(item.get('quantity') or 0):,.3f}",
                str(item.get("unit") or ""),
                _money(item.get("unit_rate", item.get("unit_price")), currency),
                _money(item.get("amount", item.get("total_cost")), currency),
            ])
        if len(table_data) == 1:
            table_data.append(["—", "—", "No itemised BoQ data was stored", "—", "—", "—", "—"])

        table = Table(table_data, repeatRows=1, colWidths=[13*mm, 35*mm, 75*mm, 24*mm, 18*mm, 32*mm, 32*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 6 * mm), Paragraph("Cost summary", styles["Heading2"])])

        summary_data = [
            ["Materials", _money(material_subtotal, currency)],
            ["Labour", _money(labour_total, currency)],
            ["Transport", _money(transport_total, currency)],
            ["FINAL ESTIMATED COST", _money(total_cost, currency)],
        ]
        summary = Table(summary_data, colWidths=[70*mm, 55*mm], hAlign="LEFT")
        summary.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(summary)
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("Prepared by ZimBuild AI. Quantities and costs are estimates and should be reviewed by a qualified construction professional before procurement or construction.", styles["Italic"]))
        doc.build(story)
        buffer.seek(0)

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name).strip("_") or "project"
        filename = f"ZimBuild_BoQ_{safe_name}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
