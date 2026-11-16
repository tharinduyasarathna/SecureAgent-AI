
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.app.database import Base
from apps.api.app.models import User
from apps.api.agents.audit_models import (
    AgentInvestigation,
    AgentAuditEvent,
)
from apps.api.agents.audit_service import (
    AuditService,
    AuditLoggingError,
)


@pytest.fixture
def audit_environment():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            AgentInvestigation.__table__,
            AgentAuditEvent.__table__,
        ],
    )

    SessionFactory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with SessionFactory.begin() as db:
        owner = User(
            email=f"owner_{uuid4().hex}@example.com",
            password_hash="test-only-hash",
        )
        attacker = User(
            email=f"attacker_{uuid4().hex}@example.com",
            password_hash="test-only-hash",
        )

        db.add_all([owner, attacker])
        db.flush()

        owner_id = owner.id
        attacker_id = attacker.id

    service = AuditService(
        session_factory=SessionFactory
    )

    try:
        yield service, owner_id, attacker_id
    finally:
        engine.dispose()


def test_owner_can_read_own_investigation(audit_environment):
    service, owner_id, _ = audit_environment
    investigation_id = str(uuid4())

    service.start_investigation(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    service.record_event(
        investigation_id=investigation_id,
        event_type="tool_executed",
        status="completed",
        tool_name="analyze_security_events",
        details={"step": 1},
    )

    service.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
        severity="medium",
    )

    history = service.get_history(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    assert history is not None
    assert history["user_id"] == owner_id
    assert history["status"] == "completed"

    event_types = [
        event["event_type"]
        for event in history["events"]
    ]

    assert event_types == [
        "investigation_started",
        "tool_executed",
        "investigation_completed",
    ]


def test_other_user_cannot_read_investigation(
    audit_environment,
):
    service, owner_id, attacker_id = audit_environment
    investigation_id = str(uuid4())

    service.start_investigation(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    service.record_event(
        investigation_id=investigation_id,
        event_type="evidence_retrieved",
        status="completed",
        details={
            "document_id": 123,
            "chunk_id": 456,
            "source_count": 1,
        },
    )

    assert service.get_history(
        investigation_id=investigation_id,
        user_id=attacker_id,
    ) is None

    # Ownership checks must not remove the
    # legitimate user's access.
    assert service.get_history(
        investigation_id=investigation_id,
        user_id=owner_id,
    ) is not None


def test_unknown_investigation_does_not_leak(
    audit_environment,
):
    service, _, attacker_id = audit_environment

    history = service.get_history(
        investigation_id=str(uuid4()),
        user_id=attacker_id,
    )

    assert history is None


def test_invalid_user_id_is_rejected(audit_environment):
    service, _, _ = audit_environment

    for invalid_id in [0, -1, True, "1", None]:
        with pytest.raises(
            AuditLoggingError,
            match="Invalid authenticated user",
        ):
            service.get_history(
                investigation_id=str(uuid4()),
                user_id=invalid_id,
            )


def test_finalized_investigation_rejects_new_events(
    audit_environment,
):
    service, owner_id, _ = audit_environment
    investigation_id = str(uuid4())

    service.start_investigation(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    service.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
    )

    with pytest.raises(
        AuditLoggingError,
        match="Investigation already finalized",
    ):
        service.record_event(
            investigation_id=investigation_id,
            event_type="tool_executed",
            status="completed",
        )


def test_audit_metadata_rejects_sensitive_fields(
    audit_environment,
):
    service, owner_id, _ = audit_environment
    investigation_id = str(uuid4())

    service.start_investigation(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    with pytest.raises(
        AuditLoggingError,
        match="Unsupported audit metadata",
    ):
        service.record_event(
            investigation_id=investigation_id,
            event_type="tool_executed",
            status="completed",
            details={
                "api_key": "should-not-be-stored",
            },
        )

    history = service.get_history(
        investigation_id=investigation_id,
        user_id=owner_id,
    )

    assert len(history["events"]) == 1
    assert history["events"][0]["event_type"] == (
        "investigation_started"
    )
