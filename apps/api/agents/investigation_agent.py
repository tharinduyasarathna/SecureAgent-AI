
from typing import Any

from apps.api.agents.security_tools import (
    create_security_tool_registry,
)
from apps.api.agents.tool_planner import (
    select_security_tool,
    AgentPlanningError,
)


class InvestigationAgent:
    def __init__(
        self,
        *,
        client: Any,
        model: str,
    ):
        self.client = client
        self.model = model
        self.registry = create_security_tool_registry()

    def investigate(
        self,
        *,
        request: str,
        events: list[dict],
        granted_permissions: set[str],
    ) -> dict:
        """
        Execute at most one approved read-only tool.

        The events and permissions must be supplied
        by trusted backend code, not by the LLM.
        """

        if not isinstance(events, list):
            raise ValueError("Events must be a list")

        if len(events) > 1000:
            raise ValueError("Too many events")

        if not isinstance(granted_permissions, set):
            raise ValueError(
                "Permissions must be a set"
            )

        tool_name = select_security_tool(
            request=request,
            client=self.client,
            model=self.model,
        )

        if tool_name == "none":
            return {
                "status": "no_tool_selected",
                "tool_name": None,
                "result": None,
            }

        if tool_name == "analyze_security_logs":
            arguments = {"events": events}

        elif tool_name == "summarize_log_statistics":
            total_events = len(events)

            failed_logins = sum(
                1
                for event in events
                if isinstance(event, dict)
                and event.get("event_type")
                == "login_failure"
            )

            arguments = {
                "total_events": total_events,
                "failed_logins": failed_logins,
            }

        else:
            raise AgentPlanningError(
                "Unexpected tool selection"
            )

        result = self.registry.execute(
            tool_name,
            granted_permissions=granted_permissions,
            arguments=arguments,
        )

        return {
            "status": "completed",
            "tool_name": tool_name,
            "result": result,
        }
