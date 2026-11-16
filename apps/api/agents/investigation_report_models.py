
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "agent_investigations.id",
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

    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    report_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="1.0",
    )

    report_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        Index(
            "ix_investigation_reports_user_created",
            "user_id",
            "created_at",
        ),
    )
