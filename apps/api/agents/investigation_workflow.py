
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
    """
    Bounded, read-only security investigation.

    The LLM selects an initial tool.
    The backend executes at most two approved tools.
    """

    MAX_STEPS = 2

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

        if not isinstance(
            granted_permissions, set
        ):
            raise ValueError(
                "Invalid permissions"
            )

        # Fail closed before calling the LLM.
        if (
            "security:read"
            not in granted_permissions
        ):
            raise PermissionError(
                "Missing security:read permission"
            )

        if investigation_id is None:
            investigation_id = str(uuid4())
        else:
            if not isinstance(
                investigation_id, str
            ):
                raise ValueError(
                    "Invalid investigation_id"
                )

            try:
                investigation_id = str(
                    UUID(investigation_id)
                )
            except (
                ValueError,
                AttributeError,
            ) as exc:
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
                    "failed_logins": sum(
                        1
                        for event in events
                        if (
                            isinstance(event, dict)
                            and event.get("event_type")
                            == "login_failure"
                        )
                    ),
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

        analysis = results[
            "analyze_security_logs"
        ]

        statistics = dict(
            results["summarize_log_statistics"]
        )

        severity_order = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        findings = analysis["findings"]

        severity = max(
            (
                finding["severity"]
                for finding in findings
            ),
            key=lambda value: (
                severity_order[value]
            ),
            default="low",
        )

        # Preserve the statistics tool's independent
        # indicator while exposing a finding-aware
        # overall risk indicator.
        statistics["statistical_risk_indicator"] = (
            statistics.get("risk_indicator")
        )

        statistics["risk_indicator"] = (
            "elevated"
            if severity in {
                "medium",
                "high",
                "critical",
            }
            else "not_elevated"
        )

        statistics["finding_based_severity"] = (
            severity
        )

        report = {
            "summary": (
                f"Analyzed "
                f"{analysis['total_events']} "
                f"security events and identified "
                f"{analysis['finding_count']} "
                f"findings."
            ),
            "severity": severity,
            "findings": findings,
            "authentication_statistics": (
                statistics
            ),
            "event_counts": (
                analysis["event_counts"]
            ),
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
