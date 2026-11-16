
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.app.database import Base
from apps.api.app.models import User
from apps.api.agents.audit_models import (
    AgentInvestigation,
    AgentAuditEvent,
)
from apps.api.agents.audit_service import AuditService
from apps.api.agents.audited_workflow import (
    AuditedInvestigationWorkflow,
)


@pytest.fixture
def audit_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            AgentInvestigation.__table__,
            AgentAuditEvent.__table__,
        ],
    )

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with factory.begin() as db:
        db.add(User(
            id=2,
            email="recovery@example.test",
            password_hash="synthetic-test-value",
        ))

    yield AuditService(session_factory=factory), factory

    engine.dispose()


def create_started(audit):
    investigation_id = str(uuid4())

    audit.start_investigation(
        investigation_id=investigation_id,
        user_id=2,
    )

    return investigation_id


def make_workflow(audit):
    workflow = AuditedInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
        audit_service=audit,
    )

    workflow.workflow.run = AsyncMock()

    return workflow


def run_args():
    return {
        "db": Mock(),
        "user_id": 2,
        "request": "Investigate suspicious logins",
        "events": [],
        "granted_permissions": {"security:read"},
    }


@pytest.mark.asyncio
async def test_audit_start_failure_blocks_agent():
    audit = Mock()

    audit.start_investigation.side_effect = (
        RuntimeError("Synthetic database outage")
    )

    workflow = make_workflow(audit)

    with pytest.raises(RuntimeError):
        await workflow.run(**run_args())

    workflow.workflow.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_failure_records_safe_error(audit_db):
    audit, factory = audit_db

    workflow = make_workflow(audit)

    workflow.workflow.run.side_effect = RuntimeError(
        "Synthetic internal secret: DO_NOT_LOG"
    )

    with pytest.raises(RuntimeError):
        await workflow.run(**run_args())

    with factory() as db:
        record = db.execute(
            select(AgentInvestigation)
            .where(AgentInvestigation.user_id == 2)
        ).scalar_one()

    history = audit.get_history(
        investigation_id=record.id,
        user_id=2,
    )

    assert history["status"] == "failed"

    serialized = str(history)

    assert "DO_NOT_LOG" not in serialized
    assert "INVESTIGATION_FAILED" in serialized


def test_interrupted_investigation_remains_started(
    audit_db,
):
    audit, _ = audit_db

    investigation_id = create_started(audit)

    # Simulate termination before finalization:
    # no completion/failure call is made.
    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    assert history["status"] == "started"
    assert history["completed_at"] is None
    assert len(history["events"]) == 1


def test_stale_investigation_can_be_identified(
    audit_db,
):
    audit, factory = audit_db

    investigation_id = create_started(audit)

    old_time = datetime.now(timezone.utc) - timedelta(
        hours=2
    )

    with factory.begin() as db:
        record = db.get(
            AgentInvestigation,
            investigation_id,
        )
        record.started_at = old_time

    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=30
    )

    with factory() as db:
        stale = db.execute(
            select(AgentInvestigation).where(
                AgentInvestigation.status == "started",
                AgentInvestigation.started_at < cutoff,
            )
        ).scalars().all()

    assert any(
        record.id == investigation_id
        for record in stale
    )


def test_finalized_investigation_not_stale(
    audit_db,
):
    audit, factory = audit_db

    investigation_id = create_started(audit)

    audit.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
        severity="medium",
    )

    cutoff = datetime.now(timezone.utc) + timedelta(
        minutes=1
    )

    with factory() as db:
        stale = db.execute(
            select(AgentInvestigation).where(
                AgentInvestigation.status == "started",
                AgentInvestigation.started_at < cutoff,
            )
        ).scalars().all()

    assert not any(
        record.id == investigation_id
        for record in stale
    )


def test_committed_events_survive_later_failure(
    audit_db,
):
    audit, _ = audit_db

    investigation_id = create_started(audit)

    audit.record_event(
        investigation_id=investigation_id,
        event_type="tool_executed",
        status="completed",
        tool_name="analyze_security_logs",
        details={"step": 1},
    )

    # Simulate failure after the first tool's
    # audit event has already committed.
    audit.finish_investigation(
        investigation_id=investigation_id,
        status="failed",
        error_code="INVESTIGATION_FAILED",
    )

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    event_types = [
        event["event_type"]
        for event in history["events"]
    ]

    assert "tool_executed" in event_types
    assert "investigation_failed" in event_types
    assert history["status"] == "failed"



from apps.api.agents.audit_service import AuditLoggingError


def make_stale(factory, investigation_id, minutes=120):
    with factory.begin() as db:
        record = db.get(
            AgentInvestigation,
            investigation_id,
        )
        record.started_at = (
            datetime.now(timezone.utc)
            - timedelta(minutes=minutes)
        )


def test_recover_stale_investigation(audit_db):
    audit, factory = audit_db
    investigation_id = create_started(audit)

    make_stale(factory, investigation_id)

    recovered = audit.recover_stale_investigations(
        timeout_minutes=60
    )

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    assert recovered == 1
    assert history["status"] == "failed"
    assert history["completed_at"] is not None

    assert history["events"][-1]["details"] == {
        "error_code": "INVESTIGATION_TIMEOUT"
    }


def test_recent_investigation_not_recovered(audit_db):
    audit, _ = audit_db
    investigation_id = create_started(audit)

    recovered = audit.recover_stale_investigations(
        timeout_minutes=60
    )

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    assert recovered == 0
    assert history["status"] == "started"


def test_completed_investigation_not_recovered(audit_db):
    audit, factory = audit_db
    investigation_id = create_started(audit)

    make_stale(factory, investigation_id)

    audit.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
        severity="medium",
    )

    recovered = audit.recover_stale_investigations()

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    assert recovered == 0
    assert history["status"] == "completed"


def test_recovery_is_idempotent(audit_db):
    audit, factory = audit_db
    investigation_id = create_started(audit)

    make_stale(factory, investigation_id)

    assert audit.recover_stale_investigations() == 1
    assert audit.recover_stale_investigations() == 0

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    failures = [
        event
        for event in history["events"]
        if event["event_type"] == "investigation_failed"
    ]

    assert len(failures) == 1


def test_recovery_preserves_existing_events(audit_db):
    audit, factory = audit_db
    investigation_id = create_started(audit)

    audit.record_event(
        investigation_id=investigation_id,
        event_type="tool_executed",
        status="completed",
        tool_name="analyze_security_logs",
        details={"step": 1},
    )

    make_stale(factory, investigation_id)

    assert audit.recover_stale_investigations() == 1

    history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    event_types = [
        event["event_type"]
        for event in history["events"]
    ]

    assert "investigation_started" in event_types
    assert "tool_executed" in event_types
    assert "investigation_failed" in event_types


def test_recovery_respects_batch_size(audit_db):
    audit, factory = audit_db

    for _ in range(3):
        investigation_id = create_started(audit)
        make_stale(factory, investigation_id)

    assert audit.recover_stale_investigations(
        batch_size=2
    ) == 2

    assert audit.recover_stale_investigations(
        batch_size=2
    ) == 1


@pytest.mark.parametrize(
    "timeout_minutes,batch_size",
    [
        (0, 100),
        (-1, 100),
        (True, 100),
        (60, 0),
        (60, 1001),
        (60, True),
    ],
)
def test_recovery_rejects_invalid_parameters(
    audit_db,
    timeout_minutes,
    batch_size,
):
    audit, _ = audit_db

    with pytest.raises(AuditLoggingError):
        audit.recover_stale_investigations(
            timeout_minutes=timeout_minutes,
            batch_size=batch_size,
        )
