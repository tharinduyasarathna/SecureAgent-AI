
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class InvestigationReview(Base):
    __tablename__ = "investigation_reviews"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "investigation_reports.investigation_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    review_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    reviewer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending', 'approved', 'rejected', 'not_required')",
            name="valid_investigation_review_status",
        ),
        CheckConstraint(
            "("
            "status = 'pending' "
            "AND review_required = TRUE "
            "AND reviewer_id IS NULL "
            "AND reviewed_at IS NULL"
            ") OR ("
            "status = 'not_required' "
            "AND review_required = FALSE "
            "AND reviewer_id IS NULL "
            "AND reviewed_at IS NULL"
            ") OR ("
            "status IN ('approved', 'rejected') "
            "AND review_required = TRUE "
            "AND reviewer_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL"
            ")",
            name="valid_review_state",
        ),
    )


class InvestigationReviewEvent(Base):
    __tablename__ = "investigation_review_events"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "investigation_reviews.investigation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    actor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        Index(
            "ix_review_events_investigation",
            "investigation_id",
            "id",
        ),
        CheckConstraint(
            "action IN ('approved', 'rejected')",
            name="valid_review_event_action",
        ),
    )
