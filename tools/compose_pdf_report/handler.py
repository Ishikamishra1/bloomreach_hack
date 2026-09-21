"""
compose_pdf_report — the Report Composer, mirroring the reference diagram's
`compose_pdf_report (ReportLab)` box exactly.

Takes the ranked Top 5-6 opportunities (already scored by the
gap_scoring_agent) and renders them into a draft PDF report, then stores
it in S3 and returns a reference to it.

Note: reportlab is not in the Python standard library — package it as a
Lambda layer or bundle it with the deployment artifact (see
tools/compose_pdf_report/requirements.txt).
"""
import io
import json
import os
import uuid

import boto3
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

s3 = boto3.client("s3")
BUCKET = os.environ.get("DATA_BUCKET_NAME")


def lambda_handler(event, context):
    ranked_opportunities = event.get("ranked_opportunities", {}).get("opportunities", [])
    therapeutic_area = event.get("therapeutic_area", "Unknown")

    pdf_bytes = _render_pdf(therapeutic_area, ranked_opportunities)

    key = f"reports/{therapeutic_area.lower()}/{uuid.uuid4()}.pdf"
    if BUCKET:
        s3.put_object(Bucket=BUCKET, Key=key, Body=pdf_bytes, ContentType="application/pdf")

    return {
        "tool": "compose_pdf_report",
        "therapeutic_area": therapeutic_area,
        "report_s3_key": key if BUCKET else None,
        "opportunity_count": len(ranked_opportunities),
        "disclaimer": (
            "This is a decision-support prioritization draft, not a "
            "guarantee of drug success, a clinical prediction, or a "
            "regulatory prediction. A human researcher must review and "
            "validate before any resource is committed."
        ),
    }


def _render_pdf(therapeutic_area: str, opportunities: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER)
    styles = getSampleStyleSheet()
    flow = []

    flow.append(Paragraph(f"TheraScout — {therapeutic_area} Opportunity Report", styles["Title"]))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(
        "Draft for researcher review. Not a guarantee of drug success, "
        "clinical prediction, or regulatory prediction.",
        styles["Italic"],
    ))
    flow.append(Spacer(1, 20))

    if opportunities:
        table_data = [["#", "Opportunity", "Score", "Rationale"]]
        for i, opp in enumerate(opportunities[:6], start=1):
            table_data.append([
                str(i),
                opp.get("name", "—"),
                str(opp.get("score", "—")),
                Paragraph(opp.get("rationale", "—")[:300], styles["BodyText"]),
            ])
        table = Table(table_data, colWidths=[25, 120, 45, 300])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E2A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        flow.append(table)
    else:
        flow.append(Paragraph("No ranked opportunities were returned.", styles["BodyText"]))

    doc.build(flow)
    return buf.getvalue()
