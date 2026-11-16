
import json
from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.agents.investigation_report_service import (
    InvestigationReportService,
)
from apps.api.agents.investigation_review_models import (
    InvestigationReview,
)
from apps.api.agents.report_export_models import (
    ReportExportEvent,
)


class ReportExportService:
    def __init__(self, db: Session):
        self.db = db

    def export(
        self,
        *,
        investigation_id: str,
        user_id: int,
        export_format: str,
    ) -> dict:
        if export_format not in {"pdf", "json"}:
            raise ValueError("Unsupported export format")

        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid user")

        investigation_id = (
            InvestigationReportService.validate_id(
                investigation_id
            )
        )

        report = InvestigationReportService(
            self.db
        ).get(
            investigation_id=investigation_id,
            user_id=user_id,
        )

        if report is None:
            raise FileNotFoundError(
                "Investigation report not found"
            )

        review = self.db.scalar(
            select(InvestigationReview).where(
                InvestigationReview.investigation_id
                == investigation_id,
                InvestigationReview.user_id == user_id,
            )
        )

        if review is None:
            raise PermissionError(
                "Review record missing. Export denied."
            )

        if review.review_required:
            if review.status != "approved":
                raise PermissionError(
                    "Human approval is required before export."
                )
        elif review.status != "not_required":
            raise PermissionError(
                "Invalid review state. Export denied."
            )

        payload = {
            **report,
            "review": {
                "status": review.status,
                "review_required": review.review_required,
                "reviewer_id": review.reviewer_id,
                "review_notes": review.review_notes,
                "reviewed_at": (
                    review.reviewed_at.isoformat()
                    if review.reviewed_at
                    else None
                ),
            },
            "exported_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if export_format == "json":
            content = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ).encode("utf-8")

            media_type = "application/json"

        else:
            content = self._render_pdf(payload)
            media_type = "application/pdf"

        event = ReportExportEvent(
            investigation_id=investigation_id,
            user_id=user_id,
            export_format=export_format,
        )

        try:
            self.db.add(event)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "content": content,
            "filename": (
                f"secureagent-report-"
                f"{investigation_id}.{export_format}"
            ),
            "media_type": media_type,
        }

    @staticmethod
    def _render_pdf(payload: dict) -> bytes:
        stream = BytesIO()

        document = SimpleDocTemplate(
            stream,
            pagesize=(595.28, 841.89),
            rightMargin=48,
            leftMargin=48,
            topMargin=52,
            bottomMargin=48,
            title="SecureAgent AI Investigation Report",
        )

        styles = getSampleStyleSheet()

        styles.add(
            ParagraphStyle(
                name="SecureAgentTitle",
                parent=styles["Title"],
                fontSize=18,
                leading=24,
                textColor=colors.HexColor("#14243A"),
                spaceAfter=15,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SecureAgentBody",
                parent=styles["BodyText"],
                fontSize=9,
                leading=14,
                spaceAfter=7,
                wordWrap="CJK",
            )
        )

        styles.add(
            ParagraphStyle(
                name="SecureAgentSmall",
                parent=styles["BodyText"],
                fontSize=8,
                leading=12,
                textColor=colors.HexColor("#475569"),
                spaceAfter=6,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SecureAgentFooter",
                parent=styles["BodyText"],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.grey,
            )
        )

        story = [
            Paragraph(
                "SecureAgent AI | Investigation Report",
                styles["SecureAgentTitle"],
            )
        ]

        def add_field(label: str, value):
            if isinstance(value, (dict, list)):
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )

            value = str(
                value
                if value is not None
                else "Not available"
            )

            value = escape(value[:50000]).replace(
                "\n",
                "<br/>",
            )

            story.append(
                Paragraph(
                    f"<b>{escape(label)}:</b> {value}",
                    styles["SecureAgentBody"],
                )
            )

        add_field(
            "Investigation ID",
            payload["investigation_id"],
        )

        add_field(
            "Severity",
            payload["severity"],
        )

        add_field(
            "Report Version",
            payload["report_version"],
        )

        add_field(
            "Created",
            payload["created_at"],
        )

        add_field(
            "Exported At",
            payload["exported_at"],
        )

        story.append(Spacer(1, 12))

        story.append(
            Paragraph(
                "Human Review",
                styles["Heading2"],
            )
        )

        review = payload["review"]

        for key in (
            "status",
            "review_required",
            "reviewer_id",
            "reviewed_at",
            "review_notes",
        ):
            add_field(
                key.replace("_", " ").title(),
                review.get(key),
            )

        story.append(Spacer(1, 12))

        story.append(
            Paragraph(
                "Investigation Findings",
                styles["Heading2"],
            )
        )

        structured_report = payload.get(
            "structured_report"
        )

        if isinstance(structured_report, dict):
            for key, value in structured_report.items():
                add_field(
                    key.replace("_", " ").title(),
                    value,
                )
        else:
            add_field(
                "Report",
                structured_report,
            )

        def draw_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawCentredString(
                297.64,
                26,
                f"SecureAgent AI | Page {doc.page}",
            )
            canvas.restoreState()

        document.build(
            story,
            onFirstPage=draw_footer,
            onLaterPages=draw_footer,
        )

        return stream.getvalue()
