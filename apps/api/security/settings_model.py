
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)

from sqlalchemy.orm import declarative_base


Base = declarative_base()


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    enable_security_agent = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    enable_rag_agent = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    enable_report_agent = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    require_human_review = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    default_severity_threshold = Column(
        String(10),
        nullable=False,
        default="medium",
    )

    max_investigation_events = Column(
        Integer,
        nullable=False,
        default=100,
    )

    auto_generate_report = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "default_severity_threshold IN "
            "('low', 'medium', 'high', 'critical')",
            name="valid_severity_threshold",
        ),
        CheckConstraint(
            "max_investigation_events BETWEEN 1 AND 10000",
            name="valid_event_limit",
        ),
    )
