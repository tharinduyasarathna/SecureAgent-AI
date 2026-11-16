
from apps.api.agents.tool_registry import (
    SecureToolRegistry,
    ToolDefinition,
)

from apps.api.agents.log_analyzer import analyze_security_logs


def summarize_log_statistics(
    *,
    total_events: int,
    failed_logins: int,
) -> dict:
    if (
        type(total_events) is not int
        or type(failed_logins) is not int
        or total_events < 0
        or failed_logins < 0
        or failed_logins > total_events
    ):
        raise ValueError("Invalid event counts")

    failure_rate = (
        round(failed_logins / total_events * 100, 2)
        if total_events > 0
        else 0.0
    )

    return {
        "total_events": total_events,
        "failed_logins": failed_logins,
        "failure_rate_percent": failure_rate,
        "risk_indicator": (
            "elevated"
            if total_events >= 10 and failure_rate >= 50
            else "not_elevated"
        ),
    }


def create_security_tool_registry():
    registry = SecureToolRegistry()

    registry.register(
        ToolDefinition(
            name="summarize_log_statistics",
            description=(
                "Calculate authentication failure statistics "
                "from supplied aggregate event counts."
            ),
            handler=summarize_log_statistics,
            permission="security:read",
        )
    )

    registry.register(
    ToolDefinition(
        name="analyze_security_logs",
        description=(
            "Analyze structured synthetic security events "
            "and identify suspicious authentication "
            "and malware activity."
        ),
        handler=analyze_security_logs,
        permission="security:read",
        )
    )

    return registry
