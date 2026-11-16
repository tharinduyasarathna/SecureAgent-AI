
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.api.agents.investigation_workflow import (
    InvestigationWorkflow,
)
from apps.api.agents.tool_planner import (
    AgentPlanningError,
)


def make_client(tool_name):
    client = Mock()
    client.responses.create.return_value = (
        SimpleNamespace(
            output_text=json.dumps({
                "tool_name": tool_name
            })
        )
    )
    return client


def make_events():
    return [
        {
            "timestamp": "2026-11-16T12:00:00Z",
            "event_type": "login_failure",
            "source_ip": "192.0.2.10",
        }
        for _ in range(6)
    ]


def make_workflow(tool_name):
    return InvestigationWorkflow(
        client=make_client(tool_name),
        model="mock-model",
    )


def test_two_step_investigation():
    workflow = make_workflow(
        "analyze_security_logs"
    )

    result = workflow.run(
        request="Investigate failed logins",
        events=make_events(),
        granted_permissions={"security:read"},
    )

    assert result["status"] == "completed"
    assert len(result["steps"]) == 2
    assert result["report"]["severity"] == "medium"
    assert result["report"]["findings"][0]["count"] == 6


def test_statistics_selected_first():
    workflow = make_workflow(
        "summarize_log_statistics"
    )

    result = workflow.run(
        request="Summarize login activity",
        events=make_events(),
        granted_permissions={"security:read"},
    )

    assert result["steps"][0]["tool_name"] == (
        "summarize_log_statistics"
    )
    assert result["steps"][1]["tool_name"] == (
        "analyze_security_logs"
    )


def test_permission_denied_before_llm_call():
    client = make_client("analyze_security_logs")

    workflow = InvestigationWorkflow(
        client=client,
        model="mock-model",
    )

    with pytest.raises(PermissionError):
        workflow.run(
            request="Investigate logs",
            events=make_events(),
            granted_permissions=set(),
        )

    client.responses.create.assert_not_called()


def test_no_tool_selected():
    workflow = make_workflow("none")

    result = workflow.run(
        request="Write a poem",
        events=make_events(),
        granted_permissions={"security:read"},
    )

    assert result["status"] == "no_tool_selected"
    assert result["steps"] == []


def test_unauthorized_tool_rejected():
    workflow = make_workflow("execute_shell")

    with pytest.raises(AgentPlanningError):
        workflow.run(
            request="Run a shell command",
            events=make_events(),
            granted_permissions={"security:read"},
        )


def test_malware_severity_high():
    workflow = make_workflow(
        "analyze_security_logs"
    )

    result = workflow.run(
        request="Investigate malware",
        events=[
            {
                "timestamp": "2026-11-16T12:00:00Z",
                "event_type": "malware_detected",
                "source_ip": "192.0.2.20",
            }
        ],
        granted_permissions={"security:read"},
    )

    assert result["report"]["severity"] == "high"


def test_empty_events():
    workflow = make_workflow(
        "analyze_security_logs"
    )

    result = workflow.run(
        request="Analyze empty logs",
        events=[],
        granted_permissions={"security:read"},
    )

    assert result["report"]["severity"] == "low"
    assert result["report"]["findings"] == []


def test_too_many_events_rejected():
    workflow = make_workflow(
        "analyze_security_logs"
    )

    with pytest.raises(ValueError):
        workflow.run(
            request="Analyze logs",
            events=make_events() * 200,
            granted_permissions={"security:read"},
        )
