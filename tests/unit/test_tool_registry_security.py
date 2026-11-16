
from dataclasses import replace
from unittest.mock import Mock

import pytest

from apps.api.agents.tool_registry import (
    SecureToolRegistry,
    ToolDefinition,
    ToolSecurityError,
)
from apps.api.agents.security_tools import (
    create_security_tool_registry,
    summarize_log_statistics,
)


def make_tool(
    handler=None,
    *,
    name="safe_tool",
    permission="security:read",
    read_only=True,
):
    return ToolDefinition(
        name=name,
        description="Test-only read-only security tool",
        handler=handler if handler is not None else Mock(),
        permission=permission,
        read_only=read_only,
    )


def test_authorized_tool_executes_with_arguments():
    registry = SecureToolRegistry()
    handler = Mock(return_value={"status": "ok"})

    registry.register(make_tool(handler))

    result = registry.execute(
        "safe_tool",
        granted_permissions={"security:read"},
        arguments={"count": 5},
    )

    assert result == {"status": "ok"}
    handler.assert_called_once_with(count=5)


@pytest.mark.parametrize(
    "permissions",
    [
        set(),
        {"security:write"},
        {"admin:write"},
        {"security:admin"},
    ],
)
def test_missing_permission_never_calls_handler(permissions):
    registry = SecureToolRegistry()
    handler = Mock()

    registry.register(make_tool(handler))

    with pytest.raises(
        ToolSecurityError,
        match="Missing permission",
    ):
        registry.execute(
            "safe_tool",
            granted_permissions=permissions,
            arguments={"count": 5},
        )

    handler.assert_not_called()


def test_unknown_tool_is_rejected():
    registry = SecureToolRegistry()

    with pytest.raises(
        ToolSecurityError,
        match="Unknown or unauthorized tool",
    ):
        registry.execute(
            "delete_security_logs",
            granted_permissions={"security:read"},
        )


def test_write_tool_registration_is_rejected():
    registry = SecureToolRegistry()
    handler = Mock()

    with pytest.raises(
        ToolSecurityError,
        match="Only read-only tools",
    ):
        registry.register(
            make_tool(
                handler,
                name="delete_security_logs",
                read_only=False,
            )
        )

    assert registry.list_tools() == []
    handler.assert_not_called()


def test_duplicate_registration_is_rejected():
    registry = SecureToolRegistry()

    registry.register(make_tool())

    with pytest.raises(
        ValueError,
        match="Tool already registered",
    ):
        registry.register(make_tool())


def test_registered_tool_definitions_are_immutable():
    tool = make_tool()

    with pytest.raises(
        AttributeError,
    ):
        tool.read_only = False


def test_execution_rechecks_read_only_flag():
    registry = SecureToolRegistry()
    handler = Mock()

    tool = make_tool(handler)
    registry.register(tool)

    # Simulate internal registry corruption.
    # The execution boundary must still fail closed.
    registry._tools["safe_tool"] = replace(
        tool,
        read_only=False,
    )

    with pytest.raises(
        ToolSecurityError,
        match="Write operations are not permitted",
    ):
        registry.execute(
            "safe_tool",
            granted_permissions={"security:read"},
        )

    handler.assert_not_called()


def test_real_registry_contains_only_approved_tools():
    registry = create_security_tool_registry()

    tools = registry.list_tools()

    assert {tool["name"] for tool in tools} == {
        "analyze_security_logs",
        "summarize_log_statistics",
    }

    assert all(
        tool["permission"] == "security:read"
        for tool in tools
    )

    assert all(
        tool["read_only"] is True
        for tool in tools
    )


def test_real_statistics_tool_executes_with_permission():
    registry = create_security_tool_registry()

    result = registry.execute(
        "summarize_log_statistics",
        granted_permissions={"security:read"},
        arguments={
            "total_events": 20,
            "failed_logins": 15,
        },
    )

    assert result["total_events"] == 20
    assert result["failed_logins"] == 15
    assert result["failure_rate_percent"] == 75.0
    assert result["risk_indicator"] == "elevated"


@pytest.mark.parametrize(
    "total_events,failed_logins",
    [
        (-1, 0),
        (5, -1),
        (5, 6),
        (True, 1),
        (10, False),
    ],
)
def test_statistics_reject_invalid_counts(
    total_events,
    failed_logins,
):
    with pytest.raises(
        ValueError,
        match="Invalid event counts",
    ):
        summarize_log_statistics(
            total_events=total_events,
            failed_logins=failed_logins,
        )


def test_handler_exceptions_are_not_silently_ignored():
    registry = SecureToolRegistry()

    handler = Mock(
        side_effect=RuntimeError("Synthetic handler failure")
    )

    registry.register(make_tool(handler))

    with pytest.raises(
        RuntimeError,
        match="Synthetic handler failure",
    ):
        registry.execute(
            "safe_tool",
            granted_permissions={"security:read"},
        )

    handler.assert_called_once()
