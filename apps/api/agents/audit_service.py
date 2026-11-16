
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from apps.api.app.database import SessionLocal
from apps.api.agents.audit_models import (
    AgentInvestigation,
    AgentAuditEvent,
)


ALLOWED_EVENT_TYPES = {
    "investigation_started",
    "tool_selected",
    "tool_executed",
    "evidence_retrieved",
    "evidence_synthesis",
    "authorization_denied",
    "investigation_completed",
    "investigation_failed",
}

ALLOWED_STATUSES = {
    "started",
    "completed",
    "failed",
    "denied",
}

ALLOWED_DETAIL_KEYS = {
    "step",
    "document_id",
    "chunk_id",
    "source_count",
    "error_code",
}

ALLOWED_SEVERITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


class AuditLoggingError(Exception):
    """Raised for invalid audit operations."""


def utc_now():
    return datetime.now(timezone.utc)


def validate_investigation_id(value: str) -> str:
    if not isinstance(value, str):
        raise AuditLoggingError(
            "Invalid investigation ID"
        )

    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise AuditLoggingError(
            "Invalid investigation ID"
        ) from exc

    if str(parsed) != value:
        raise AuditLoggingError(
            "Investigation ID must be canonical UUID"
        )

    return value


def validate_details(details: dict | None) -> dict:
    if details is None:
        return {}

    if not isinstance(details, dict):
        raise AuditLoggingError(
            "Audit details must be a dictionary"
        )

    if not set(details).issubset(ALLOWED_DETAIL_KEYS):
        raise AuditLoggingError(
            "Unsupported audit metadata"
        )

    clean = {}

    for key, value in details.items():
        if key in {
            "step",
            "document_id",
            "chunk_id",
            "source_count",
        }:
            if type(value) is not int or value < 0:
                raise AuditLoggingError(
                    f"Invalid metadata: {key}"
                )

        elif key == "error_code":
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 64
                or not all(
                    c.isupper()
                    or c.isdigit()
                    or c == "_"
                    for c in value
                )
            ):
                raise AuditLoggingError(
                    "Invalid error code"
                )

        clean[key] = value

    return clean


class AuditService:
    """
    Persistent audit service.

    Each method uses its own database transaction.

    Never store:
    - API keys
    - Passwords
    - Raw document contents
    - Full prompts
    - Unrestricted LLM responses

    Recovery must be invoked by a trusted maintenance
    process, not by an ordinary user-facing API route.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.session_factory = session_factory

    def start_investigation(
        self,
        *,
        investigation_id: str,
        user_id: int,
    ) -> str:
        validate_investigation_id(investigation_id)

        if type(user_id) is not int or user_id <= 0:
            raise AuditLoggingError(
                "Invalid authenticated user"
            )

        with self.session_factory() as db:
            with db.begin():
                record = AgentInvestigation(
                    id=investigation_id,
                    user_id=user_id,
                    status="started",
                )

                db.add(record)

                db.add(
                    AgentAuditEvent(
                        investigation_id=investigation_id,
                        event_type="investigation_started",
                        status="started",
                        details={},
                    )
                )

        return investigation_id

    def record_event(
        self,
        *,
        investigation_id: str,
        event_type: str,
        status: str,
        tool_name: str | None = None,
        details: dict | None = None,
    ) -> None:
        validate_investigation_id(investigation_id)

        if event_type not in ALLOWED_EVENT_TYPES:
            raise AuditLoggingError(
                "Unsupported audit event type"
            )

        if status not in ALLOWED_STATUSES:
            raise AuditLoggingError(
                "Unsupported audit status"
            )

        if tool_name is not None:
            if (
                not isinstance(tool_name, str)
                or not tool_name
                or len(tool_name) > 128
                or not all(
                    c.isalnum() or c == "_"
                    for c in tool_name
                )
            ):
                raise AuditLoggingError(
                    "Invalid tool name"
                )

        safe_details = validate_details(details)

        with self.session_factory() as db:
            with db.begin():
                investigation = db.execute(
                    select(AgentInvestigation)
                    .where(
                        AgentInvestigation.id
                        == investigation_id
                    )
                    .with_for_update()
                ).scalar_one_or_none()

                if investigation is None:
                    raise AuditLoggingError(
                        "Investigation not found"
                    )

                if investigation.status != "started":
                    raise AuditLoggingError(
                        "Investigation already finalized"
                    )

                db.add(
                    AgentAuditEvent(
                        investigation_id=investigation_id,
                        event_type=event_type,
                        tool_name=tool_name,
                        status=status,
                        details=safe_details,
                    )
                )

    def finish_investigation(
        self,
        *,
        investigation_id: str,
        status: str,
        severity: str | None = None,
        error_code: str | None = None,
    ) -> None:
        validate_investigation_id(investigation_id)

        if status not in {
            "completed",
            "failed",
            "denied",
        }:
            raise AuditLoggingError(
                "Invalid final status"
            )

        if (
            severity is not None
            and severity not in ALLOWED_SEVERITIES
        ):
            raise AuditLoggingError(
                "Invalid severity"
            )

        details = validate_details(
            {"error_code": error_code}
            if error_code is not None
            else {}
        )

        event_type = {
            "completed": "investigation_completed",
            "failed": "investigation_failed",
            "denied": "authorization_denied",
        }[status]

        with self.session_factory() as db:
            with db.begin():
                # Lock the investigation row before
                # checking and changing its status.
                # PostgreSQL honors this row lock.
                investigation = db.execute(
                    select(AgentInvestigation)
                    .where(
                        AgentInvestigation.id
                        == investigation_id
                    )
                    .with_for_update()
                ).scalar_one_or_none()

                if investigation is None:
                    raise AuditLoggingError(
                        "Investigation not found"
                    )

                if investigation.status != "started":
                    raise AuditLoggingError(
                        "Investigation already finalized"
                    )

                investigation.status = status
                investigation.severity = severity
                investigation.completed_at = utc_now()

                db.add(
                    AgentAuditEvent(
                        investigation_id=investigation_id,
                        event_type=event_type,
                        status=status,
                        details=details,
                    )
                )

    def get_history(
        self,
        *,
        investigation_id: str,
        user_id: int,
    ) -> dict | None:
        validate_investigation_id(investigation_id)

        if type(user_id) is not int or user_id <= 0:
            raise AuditLoggingError(
                "Invalid authenticated user"
            )

        with self.session_factory() as db:
            investigation = db.execute(
                select(AgentInvestigation).where(
                    AgentInvestigation.id
                    == investigation_id,
                    AgentInvestigation.user_id == user_id,
                )
            ).scalar_one_or_none()

            if investigation is None:
                return None

            events = db.execute(
                select(AgentAuditEvent)
                .where(
                    AgentAuditEvent.investigation_id
                    == investigation_id
                )
                .order_by(
                    AgentAuditEvent.created_at,
                    AgentAuditEvent.id,
                )
            ).scalars().all()

            return {
                "investigation_id": investigation.id,
                "user_id": investigation.user_id,
                "status": investigation.status,
                "severity": investigation.severity,
                "started_at": (
                    investigation.started_at.isoformat()
                ),
                "completed_at": (
                    investigation.completed_at.isoformat()
                    if investigation.completed_at
                    else None
                ),
                "events": [
                    {
                        "event_type": event.event_type,
                        "tool_name": event.tool_name,
                        "status": event.status,
                        "details": event.details,
                        "created_at": (
                            event.created_at.isoformat()
                        ),
                    }
                    for event in events
                ],
            }

    def recover_stale_investigations(
        self,
        *,
        timeout_minutes: int = 60,
        batch_size: int = 100,
    ) -> int:
        """
        Recover investigations that remain in
        'started' state beyond the timeout.

        The investigation status update and failure
        audit event are committed atomically.

        A conditional update prevents duplicate
        recovery when multiple recovery workers
        target the same investigation.

        Returns the number of recovered investigations.
        """

        if (
            type(timeout_minutes) is not int
            or timeout_minutes <= 0
        ):
            raise AuditLoggingError(
                "timeout_minutes must be a positive integer"
            )

        if (
            type(batch_size) is not int
            or not 1 <= batch_size <= 1000
        ):
            raise AuditLoggingError(
                "batch_size must be between 1 and 1000"
            )

        cutoff = utc_now() - timedelta(
            minutes=timeout_minutes
        )

        recovered = 0

        with self.session_factory() as db:
            with db.begin():
                candidate_ids = db.execute(
                    select(AgentInvestigation.id)
                    .where(
                        AgentInvestigation.status
                        == "started",
                        AgentInvestigation.started_at
                        <= cutoff,
                    )
                    .order_by(
                        AgentInvestigation.started_at,
                        AgentInvestigation.id,
                    )
                    .limit(batch_size)
                ).scalars().all()

                for investigation_id in candidate_ids:
                    # Conditional update rechecks
                    # status and age at write time.
                    result = db.execute(
                        update(AgentInvestigation)
                        .where(
                            AgentInvestigation.id
                            == investigation_id,
                            AgentInvestigation.status
                            == "started",
                            AgentInvestigation.started_at
                            <= cutoff,
                        )
                        .values(
                            status="failed",
                            severity=None,
                            completed_at=utc_now(),
                        )
                        .returning(
                            AgentInvestigation.id
                        )
                    )

                    claimed_id = (
                        result.scalar_one_or_none()
                    )

                    if claimed_id is None:
                        continue

                    db.add(
                        AgentAuditEvent(
                            investigation_id=claimed_id,
                            event_type="investigation_failed",
                            status="failed",
                            details={
                                "error_code":
                                "INVESTIGATION_TIMEOUT",
                            },
                        )
                    )

                    recovered += 1

        return recovered
