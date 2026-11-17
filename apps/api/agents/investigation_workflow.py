
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from apps.api.agents.security_tools import (
    create_security_tool_registry,
)
from apps.api.agents.tool_planner import (
    select_security_tool,
)


class InvestigationWorkflow:
    MAX_STEPS = 2

    SEVERITY_ORDER = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def __init__(
        self,
        *,
        client: Any,
        model: str,
    ):
        self.client = client
        self.model = model
        self.registry = create_security_tool_registry()

    def run(
        self,
        *,
        request: str,
        events: list[dict],
        granted_permissions: set[str],
        investigation_id: str | None = None,
    ) -> dict:
        if not isinstance(events, list):
            raise ValueError("Events must be a list")

        if len(events) > 1000:
            raise ValueError(
                "Maximum 1000 events allowed"
            )

        if not isinstance(granted_permissions, set):
            raise ValueError("Invalid permissions")

        if "security:read" not in granted_permissions:
            raise PermissionError(
                "Missing security:read permission"
            )

        if investigation_id is None:
            investigation_id = str(uuid4())
        else:
            if not isinstance(investigation_id, str):
                raise ValueError(
                    "Invalid investigation_id"
                )

            try:
                investigation_id = str(
                    UUID(investigation_id)
                )
            except (ValueError, AttributeError) as exc:
                raise ValueError(
                    "Invalid investigation_id"
                ) from exc

        first_tool = select_security_tool(
            request=request,
            client=self.client,
            model=self.model,
        )

        if first_tool == "none":
            return {
                "investigation_id": investigation_id,
                "status": "no_tool_selected",
                "steps": [],
                "report": None,
            }

        available_tools = [
            "analyze_security_logs",
            "summarize_log_statistics",
        ]

        if first_tool not in available_tools:
            raise ValueError(
                "Invalid tool selection"
            )

        ordered_tools = [
            first_tool,
            *[
                tool
                for tool in available_tools
                if tool != first_tool
            ],
        ][:self.MAX_STEPS]

        steps = []
        results = {}

        failed_login_records = sum(
            1
            for event in events
            if (
                isinstance(event, dict)
                and event.get("event_type") == "login_failure"
            )
        )

        for step_number, tool_name in enumerate(
            ordered_tools,
            start=1,
        ):
            if tool_name == "analyze_security_logs":
                arguments = {
                    "events": events,
                }
            else:
                arguments = {
                    "total_events": len(events),
                    "failed_logins": failed_login_records,
                }

            result = self.registry.execute(
                tool_name,
                granted_permissions=granted_permissions,
                arguments=arguments,
            )

            results[tool_name] = result

            steps.append({
                "step": step_number,
                "tool_name": tool_name,
                "status": "completed",
            })

        analysis = results["analyze_security_logs"]

        statistics = dict(
            results["summarize_log_statistics"]
        )

        findings = analysis["findings"]

        severity = max(
            (
                finding["severity"]
                for finding in findings
            ),
            key=lambda value: self.SEVERITY_ORDER[value],
            default="low",
        )

        total_events = analysis["total_events"]
        event_counts = analysis["event_counts"]

        failed_attempts = analysis.get(
            "failed_login_attempts",
            failed_login_records,
        )

        if (
            type(failed_attempts) is not int
            or failed_attempts < 0
        ):
            raise RuntimeError(
                "Invalid analyzed failed-login count"
            )

        statistics["statistical_risk_indicator"] = (
            statistics.get("risk_indicator")
        )

        statistics["risk_indicator"] = (
            "elevated"
            if severity in {"medium", "high", "critical"}
            else "not_elevated"
        )

        statistics["finding_based_severity"] = severity
        statistics["failed_login_records"] = (
            failed_login_records
        )
        statistics["failed_login_attempts"] = (
            failed_attempts
        )
        statistics["total_events"] = total_events

        statistics["successful_logins"] = (
            event_counts.get("login_success", 0)
        )

        statistics["failure_rate_basis"] = (
            "event_records"
        )

        security_event_types = sorted(
            event_type
            for event_type, count in event_counts.items()
            if count > 0
        )

        high_severity_findings = sum(
            1
            for finding in findings
            if finding["severity"] in {"high", "critical"}
        )

        report = {
            "summary": (
                f"Analyzed {total_events} security events "
                f"and identified {analysis['finding_count']} "
                f"findings. Overall severity: {severity}."
            ),
            "severity": severity,
            "findings": findings,
            "authentication_statistics": statistics,
            "event_counts": event_counts,
            "failed_login_attempts": failed_attempts,
            "total_events": total_events,
            "finding_count": analysis["finding_count"],
            "high_severity_findings": (
                high_severity_findings
            ),
            "security_event_types": security_event_types,
            "evidence_source": (
                "supplied_security_events"
            ),
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        return {
            "investigation_id": investigation_id,
            "status": "completed",
            "steps": steps,
            "report": report,
        }
