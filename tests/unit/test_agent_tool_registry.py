
import pytest

from apps.api.agents.security_tools import (
    create_security_tool_registry,
)
from apps.api.agents.tool_registry import (
    SecureToolRegistry,
    ToolDefinition,
    ToolSecurityError,
)


@pytest.fixture
def registry():
    return create_security_tool_registry()


def test_registered_tool_executes(registry):
    result = registry.execute(
        "summarize_log_statistics",
        granted_permissions={"security:read"},
        arguments={
            "total_events": 100,
            "failed_logins": 60,
        },
    )

    assert result["failure_rate_percent"] == 60.0
    assert result["risk_indicator"] == "elevated"


def test_unknown_tool_is_blocked(registry):
    with pytest.raises(ToolSecurityError):
        registry.execute(
            "execute_shell",
            granted_permissions={"security:read"},
        )


def test_missing_permission_is_blocked(registry):
    with pytest.raises(ToolSecurityError):
        registry.execute(
            "summarize_log_statistics",
            granted_permissions=set(),
            arguments={
                "total_events": 100,
                "failed_logins": 60,
            },
        )


def test_write_tool_registration_is_blocked():
    registry = SecureToolRegistry()

    with pytest.raises(ToolSecurityError):
        registry.register(
            ToolDefinition(
                name="delete_logs",
                description="Delete security logs",
                handler=lambda: None,
                permission="security:write",
                read_only=False,
            )
        )


def test_duplicate_registration_is_blocked(registry):
    with pytest.raises(ValueError):
        registry.register(
            ToolDefinition(
                name="summarize_log_statistics",
                description="Duplicate",
                handler=lambda: None,
                permission="security:read",
            )
        )


def test_invalid_log_counts_are_rejected(registry):
    with pytest.raises(ValueError):
        registry.execute(
            "summarize_log_statistics",
            granted_permissions={"security:read"},
            arguments={
                "total_events": 10,
                "failed_logins": 20,
            },
        )
