
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.agents.investigation_report_models import (
    InvestigationReport,
)
from apps.api.agents.investigation_review_models import (
    InvestigationReview,
    InvestigationReviewEvent,
)


class ReviewNotFoundError(Exception):
    pass


class ReviewConflictError(Exception):
    pass


class InvestigationReviewService:
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
            raise ValueError("Invalid investigation ID")

        return canonical

    @staticmethod
    def serialize(review: InvestigationReview) -> dict:
        return {
            "investigation_id": review.investigation_id,
            "user_id": review.user_id,
            "review_required": review.review_required,
            "status": review.status,
            "reviewer_id": review.reviewer_id,
            "review_notes": review.review_notes,
            "reviewed_at": (
                review.reviewed_at.isoformat()
                if review.reviewed_at
                else None
            ),
            "created_at": (
                review.created_at.isoformat()
                if review.created_at
                else None
            ),
        }

    def get(
        self,
        *,
        investigation_id: str,
        user_id: int,
    ) -> dict | None:
        investigation_id = self.validate_id(
            investigation_id
        )

        review = self.db.execute(
            select(InvestigationReview).where(
                InvestigationReview.investigation_id
                == investigation_id,
                InvestigationReview.user_id == user_id,
            )
        ).scalar_one_or_none()

        if review is None:
            return None

        return self.serialize(review)

    def decide(
        self,
        *,
        investigation_id: str,
        user_id: int,
        decision: str,
        notes: str,
    ) -> dict:
        investigation_id = self.validate_id(
            investigation_id
        )

        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid reviewer")

        if decision not in {"approved", "rejected"}:
            raise ValueError("Invalid review decision")

        if not isinstance(notes, str):
            raise ValueError("Invalid review notes")

        notes = notes.strip()

        if not 1 <= len(notes) <= 2000:
            raise ValueError(
                "Review notes must contain 1-2000 characters"
            )

        try:
            review = self.db.execute(
                select(InvestigationReview)
                .where(
                    InvestigationReview.investigation_id
                    == investigation_id,
                    InvestigationReview.user_id == user_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if review is None:
                raise ReviewNotFoundError(
                    "Review not found"
                )

            if (
                not review.review_required
                or review.status != "pending"
            ):
                raise ReviewConflictError(
                    "Review is not awaiting a decision"
                )

            report = self.db.execute(
                select(InvestigationReport).where(
                    InvestigationReport.investigation_id
                    == investigation_id,
                    InvestigationReport.user_id == user_id,
                )
            ).scalar_one_or_none()

            if report is None:
                raise ReviewNotFoundError(
                    "Report not found"
                )

            now = datetime.now(timezone.utc)

            review.status = decision
            review.reviewer_id = user_id
            review.review_notes = notes
            review.reviewed_at = now

            event = InvestigationReviewEvent(
                investigation_id=investigation_id,
                actor_id=user_id,
                action=decision,
                notes=notes,
                created_at=now,
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(review)

            return self.serialize(review)

        except Exception:
            self.db.rollback()
            raise

    def history(
        self,
        *,
        investigation_id: str,
        user_id: int,
    ) -> list[dict]:
        investigation_id = self.validate_id(
            investigation_id
        )

        review = self.db.execute(
            select(InvestigationReview).where(
                InvestigationReview.investigation_id
                == investigation_id,
                InvestigationReview.user_id == user_id,
            )
        ).scalar_one_or_none()

        if review is None:
            raise ReviewNotFoundError(
                "Review not found"
            )

        events = self.db.execute(
            select(InvestigationReviewEvent)
            .where(
                InvestigationReviewEvent.investigation_id
                == investigation_id
            )
            .order_by(
                InvestigationReviewEvent.id.asc()
            )
        ).scalars().all()

        return [
            {
                "id": event.id,
                "investigation_id": event.investigation_id,
                "actor_id": event.actor_id,
                "action": event.action,
                "notes": event.notes,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
