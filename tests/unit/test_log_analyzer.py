
import pytest

from apps.api.agents.log_analyzer import (
    analyze_security_logs,
)
from apps.api.agents.security_tools import (
    create_security_tool_registry,
)
from apps.api.agents.tool_registry import (
    ToolSecurityError,
)


def make_event(event_type, source_ip="192.0.2.10"):
    return {
        "timestamp": "2026-11-16T12:00:00Z",
        "event_type": event_type,
        "source_ip": source_ip,
    }


def test_empty_events():
    result = analyze_security_logs(events=[])

    assert result["total_events"] == 0
    assert result["finding_count"] == 0


def test_repeated_login_failures():
    events = [
        make_event("login_failure")
        for _ in range(5)
    ]

    result = analyze_security_logs(events=events)

    assert result["finding_count"] == 1
    assert result["findings"][0]["type"] == (
        "repeated_login_failures"
    )


def test_malware_detection():
    result = analyze_security_logs(
        events=[make_event("malware_detected")]
    )

    assert result["findings"][0]["severity"] == "high"


def test_invalid_event_type():
    with pytest.raises(ValueError):
        analyze_security_logs(
            events=[make_event("unknown_event")]
        )


def test_missing_timestamp():
    event = make_event("login_failure")
    del event["timestamp"]

    with pytest.raises(ValueError):
        analyze_security_logs(events=[event])


def test_naive_timestamp_rejected():
    event = make_event("login_failure")
    event["timestamp"] = "2026-11-16T12:00:00"

    with pytest.raises(ValueError):
        analyze_security_logs(events=[event])


def test_too_many_events():
    events = [
        make_event("login_success")
        for _ in range(1001)
    ]

    with pytest.raises(ValueError):
        analyze_security_logs(events=events)


def test_registry_permission_enforced():
    registry = create_security_tool_registry()

    with pytest.raises(ToolSecurityError):
        registry.execute(
            "analyze_security_logs",
            granted_permissions=set(),
            arguments={"events": []},
        )


def test_registry_executes_analyzer():
    registry = create_security_tool_registry()

    result = registry.execute(
        "analyze_security_logs",
        granted_permissions={"security:read"},
        arguments={
            "events": [
                make_event("malware_detected")
            ]
        },
    )

    assert result["finding_count"] == 1
