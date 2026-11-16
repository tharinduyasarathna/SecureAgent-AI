
from uuid import uuid4

import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
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
def audit_service():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False
        },
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
        db.add_all([
            User(
                id=1,
                email="audit1@example.test",
                password_hash="synthetic-test-value",
            ),
            User(
                id=2,
                email="audit2@example.test",
                password_hash="synthetic-test-value",
            ),
        ])

    yield AuditService(session_factory=factory)

    engine.dispose()


def test_start_investigation(audit_service):
    investigation_id = str(uuid4())

    result = audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert result == investigation_id

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert history["status"] == "started"
    assert len(history["events"]) == 1


def test_record_tool_execution(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.record_event(
        investigation_id=investigation_id,
        event_type="tool_executed",
        tool_name="analyze_security_logs",
        status="completed",
        details={"step": 1},
    )

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert len(history["events"]) == 2
    assert (
        history["events"][1]["tool_name"]
        == "analyze_security_logs"
    )


def test_evidence_access_logged(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.record_event(
        investigation_id=investigation_id,
        event_type="evidence_retrieved",
        status="completed",
        details={
            "document_id": 10,
            "chunk_id": 21,
        },
    )

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert (
        history["events"][1]["details"]["chunk_id"]
        == 21
    )


def test_finish_investigation(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
        severity="medium",
    )

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert history["status"] == "completed"
    assert history["severity"] == "medium"
    assert history["completed_at"] is not None
    assert len(history["events"]) == 2


def test_failed_investigation(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.finish_investigation(
        investigation_id=investigation_id,
        status="failed",
        error_code="TOOL_EXECUTION_FAILED",
    )

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert history["status"] == "failed"
    assert (
        history["events"][-1]["details"]["error_code"]
        == "TOOL_EXECUTION_FAILED"
    )


def test_cross_user_history_isolation(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    result = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    assert result is None


def test_sensitive_metadata_rejected(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    with pytest.raises(AuditLoggingError):
        audit_service.record_event(
            investigation_id=investigation_id,
            event_type="tool_executed",
            status="completed",
            details={
                "api_key": "must-not-be-logged"
            },
        )

    history = audit_service.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    assert len(history["events"]) == 1


def test_cannot_append_after_completion(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
    )

    with pytest.raises(AuditLoggingError):
        audit_service.record_event(
            investigation_id=investigation_id,
            event_type="tool_executed",
            status="completed",
        )


def test_invalid_user_rejected(audit_service):
    with pytest.raises(AuditLoggingError):
        audit_service.start_investigation(
            investigation_id=str(uuid4()),
            user_id=0,
        )


def test_invalid_event_type_rejected(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    with pytest.raises(AuditLoggingError):
        audit_service.record_event(
            investigation_id=investigation_id,
            event_type="arbitrary_event",
            status="completed",
        )


def test_double_finalization_rejected(audit_service):
    investigation_id = str(uuid4())

    audit_service.start_investigation(
        investigation_id=investigation_id,
        user_id=1,
    )

    audit_service.finish_investigation(
        investigation_id=investigation_id,
        status="completed",
    )

    with pytest.raises(AuditLoggingError):
        audit_service.finish_investigation(
            investigation_id=investigation_id,
            status="failed",
        )
