
from datetime import datetime, timezone

from sqlalchemy import ForeignKeyConstraint

from apps.api.agents.audit_models import (
    AgentAuditEvent,
    AgentInvestigation,
)


def test_investigation_table_name():
    assert (
        AgentInvestigation.__tablename__
        == "agent_investigations"
    )


def test_audit_event_table_name():
    assert (
        AgentAuditEvent.__tablename__
        == "agent_audit_events"
    )


def test_investigation_has_user_foreign_key():
    table = AgentInvestigation.__table__

    targets = {
        element.target_fullname
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for element in constraint.elements
    }

    assert "users.id" in targets


def test_event_has_investigation_foreign_key():
    table = AgentAuditEvent.__table__

    targets = {
        element.target_fullname
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for element in constraint.elements
    }

    assert "agent_investigations.id" in targets


def test_audit_metadata_column_exists():
    assert "details" in AgentAuditEvent.__table__.columns


def test_timestamp_columns_exist():
    investigation_columns = (
        AgentInvestigation.__table__.columns
    )
    event_columns = AgentAuditEvent.__table__.columns

    assert "started_at" in investigation_columns
    assert "completed_at" in investigation_columns
    assert "created_at" in event_columns


def test_investigation_id_is_primary_key():
    assert (
        AgentInvestigation.__table__.c.id.primary_key
    )


def test_audit_event_id_is_primary_key():
    assert AgentAuditEvent.__table__.c.id.primary_key


def test_audit_events_have_required_columns():
    columns = AgentAuditEvent.__table__.columns

    for name in (
        "investigation_id",
        "event_type",
        "tool_name",
        "status",
        "details",
        "created_at",
    ):
        assert name in columns
