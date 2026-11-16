
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.agents.audit_models import AgentInvestigation
from apps.api.agents.investigation_report_models import (
    InvestigationReport,
)
from apps.api.agents.investigation_review_models import (
    InvestigationReview,
)


class InvestigationReportService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_id(investigation_id: str) -> str:
        try:
            canonical = str(UUID(investigation_id))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(
                "Invalid investigation ID"
            ) from None

        if canonical != investigation_id:
            raise ValueError(
                "Invalid investigation ID"
            )

        return canonical

    def save(
        self,
        *,
        investigation_id: str,
        user_id: int,
        structured_report: dict,
        review_required: bool = True,
    ) -> dict:
        investigation_id = self.validate_id(
            investigation_id
        )

        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid user")

        if type(review_required) is not bool:
            raise ValueError(
                "Invalid review requirement"
            )

        if not isinstance(structured_report, dict):
            raise ValueError(
                "Invalid structured report"
            )

        if (
            structured_report.get("investigation_id")
            != investigation_id
        ):
            raise ValueError(
                "Report investigation ID mismatch"
            )

        if structured_report.get("status") != "completed":
            raise ValueError(
                "Only completed reports can be saved"
            )

        risk = structured_report.get(
            "risk_assessment"
        )

        if not isinstance(risk, dict):
            raise ValueError(
                "Missing risk assessment"
            )

        severity = risk.get("severity")

        if severity not in {
            "low",
            "medium",
            "high",
            "critical",
        }:
            raise ValueError(
                "Invalid report severity"
            )

        try:
            investigation = self.db.execute(
                select(AgentInvestigation)
                .where(
                    AgentInvestigation.id == investigation_id,
                    AgentInvestigation.user_id == user_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if investigation is None:
                raise PermissionError(
                    "Investigation not found or access denied"
                )

            if investigation.status != "completed":
                raise ValueError(
                    "Investigation has not completed"
                )

            if investigation.severity != severity:
                raise ValueError(
                    "Report severity does not match audit"
                )

            existing = self.db.get(
                InvestigationReport,
                investigation_id,
            )

            if existing is not None:
                raise ValueError(
                    "Report already saved"
                )

            record = InvestigationReport(
                investigation_id=investigation_id,
                user_id=user_id,
                severity=severity,
                report_version=str(
                    structured_report.get(
                        "report_version",
                        "1.0",
                    )
                ),
                report_data=structured_report,
            )

            review = InvestigationReview(
                investigation_id=investigation_id,
                user_id=user_id,
                review_required=review_required,
                status=(
                    "pending"
                    if review_required
                    else "not_required"
                ),
            )

            self.db.add(record)
            self.db.flush()
            self.db.add(review)
            self.db.commit()

            self.db.refresh(record)

            return self._serialize(
                record,
                review_status=review.status,
            )

        except Exception:
            self.db.rollback()
            raise

    def get(
        self,
        *,
        investigation_id: str,
        user_id: int,
    ) -> dict | None:
        investigation_id = self.validate_id(
            investigation_id
        )

        row = self.db.execute(
            select(
                InvestigationReport,
                InvestigationReview.status,
            )
            .outerjoin(
                InvestigationReview,
                InvestigationReview.investigation_id
                == InvestigationReport.investigation_id,
            )
            .where(
                InvestigationReport.investigation_id
                == investigation_id,
                InvestigationReport.user_id == user_id,
            )
        ).one_or_none()

        if row is None:
            return None

        record, review_status = row

        return self._serialize(
            record,
            review_status=review_status,
        )

    def list_reports(
        self,
        *,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid user")

        if (
            type(limit) is not int
            or not 1 <= limit <= 100
            or type(offset) is not int
            or offset < 0
        ):
            raise ValueError("Invalid pagination")

        total = self.db.scalar(
            select(func.count())
            .select_from(InvestigationReport)
            .where(
                InvestigationReport.user_id == user_id
            )
        )

        rows = self.db.execute(
            select(
                InvestigationReport,
                InvestigationReview.status,
            )
            .outerjoin(
                InvestigationReview,
                InvestigationReview.investigation_id
                == InvestigationReport.investigation_id,
            )
            .where(
                InvestigationReport.user_id == user_id
            )
            .order_by(
                InvestigationReport.created_at.desc(),
                InvestigationReport.investigation_id.desc(),
            )
            .limit(limit)
            .offset(offset)
        ).all()

        return {
            "total": total or 0,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "investigation_id": record.investigation_id,
                    "severity": record.severity,
                    "report_version": record.report_version,
                    "created_at": record.created_at.isoformat(),
                    "title": record.report_data.get(
                        "title",
                        "Security Investigation Report",
                    ),
                    "review_status": review_status,
                }
                for record, review_status in rows
            ],
        }

    @staticmethod
    def _serialize(
        record: InvestigationReport,
        *,
        review_status: str | None = None,
    ) -> dict:
        return {
            "investigation_id": record.investigation_id,
            "user_id": record.user_id,
            "severity": record.severity,
            "report_version": record.report_version,
            "created_at": record.created_at.isoformat(),
            "review_status": review_status,
            "structured_report": record.report_data,
        }
