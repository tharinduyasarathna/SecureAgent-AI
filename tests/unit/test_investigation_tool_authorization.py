
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from apps.api.agents.investigation_workflow import (
    InvestigationWorkflow,
)


def make_workflow():
    client = Mock()
    workflow = InvestigationWorkflow(
        client=client,
        model="test-model",
    )
    workflow.registry = Mock()
    return workflow, client


def test_missing_permission_fails_before_planner():
    workflow, client = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool"
    ) as planner:
        with pytest.raises(
            PermissionError,
            match="Missing security:read permission",
        ):
            workflow.run(
                request="Investigate failed logins",
                events=[],
                granted_permissions=set(),
            )

        planner.assert_not_called()
        workflow.registry.execute.assert_not_called()


@pytest.mark.parametrize(
    "permissions",
    [
        {"admin:write"},
        {"security:write"},
        {"security:admin"},
        set(),
    ],
)
def test_unrelated_permissions_do_not_grant_read(permissions):
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool"
    ) as planner:
        with pytest.raises(PermissionError):
            workflow.run(
                request="Investigate events",
                events=[],
                granted_permissions=permissions,
            )

        planner.assert_not_called()
        workflow.registry.execute.assert_not_called()


def test_unknown_tool_is_rejected():
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool",
        return_value="delete_security_logs",
    ):
        with pytest.raises(
            ValueError,
            match="Invalid tool selection",
        ):
            workflow.run(
                request="Investigate activity",
                events=[],
                granted_permissions={"security:read"},
            )

    workflow.registry.execute.assert_not_called()


def test_none_selection_executes_no_tools():
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool",
        return_value="none",
    ):
        result = workflow.run(
            request="Investigate activity",
            events=[],
            granted_permissions={"security:read"},
        )

    assert result["status"] == "no_tool_selected"
    assert result["steps"] == []
    workflow.registry.execute.assert_not_called()


@pytest.mark.parametrize(
    "selected_tool",
    [
        "analyze_security_logs",
        "summarize_log_statistics",
    ],
)
def test_only_approved_tools_execute(selected_tool):
    workflow, _ = make_workflow()

    workflow.registry.execute.side_effect = (
        lambda tool_name, **kwargs: (
            {
                "total_events": 0,
                "finding_count": 0,
                "findings": [],
                "event_counts": {},
            }
            if tool_name == "analyze_security_logs"
            else {
                "total_events": 0,
                "failed_logins": 0,
            }
        )
    )

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool",
        return_value=selected_tool,
    ):
        result = workflow.run(
            request="Investigate activity",
            events=[],
            granted_permissions={"security:read"},
        )

    assert result["status"] == "completed"
    assert len(result["steps"]) == 2

    executed = [
        call.args[0]
        for call in workflow.registry.execute.call_args_list
    ]

    assert set(executed) == {
        "analyze_security_logs",
        "summarize_log_statistics",
    }

    for call in workflow.registry.execute.call_args_list:
        assert call.kwargs["granted_permissions"] == {
            "security:read"
        }


def test_invalid_events_rejected_before_planner():
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool"
    ) as planner:
        with pytest.raises(ValueError):
            workflow.run(
                request="Investigate activity",
                events="not a list",
                granted_permissions={"security:read"},
            )

        planner.assert_not_called()


def test_event_limit_enforced():
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool"
    ) as planner:
        with pytest.raises(
            ValueError,
            match="Maximum 1000 events allowed",
        ):
            workflow.run(
                request="Investigate activity",
                events=[{}] * 1001,
                granted_permissions={"security:read"},
            )

        planner.assert_not_called()


def test_existing_investigation_id_preserved():
    workflow, _ = make_workflow()
    investigation_id = str(uuid4())

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool",
        return_value="none",
    ):
        result = workflow.run(
            request="Investigate activity",
            events=[],
            granted_permissions={"security:read"},
            investigation_id=investigation_id,
        )

    assert result["investigation_id"] == investigation_id


def test_generated_investigation_id_is_valid_uuid():
    workflow, _ = make_workflow()

    with patch(
        "apps.api.agents.investigation_workflow.select_security_tool",
        return_value="none",
    ):
        result = workflow.run(
            request="Investigate activity",
            events=[],
            granted_permissions={"security:read"},
        )

    assert str(UUID(result["investigation_id"])) == (
        result["investigation_id"]
    )
