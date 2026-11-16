
from typing import Any

from apps.api.agents.investigation_workflow import (
    InvestigationWorkflow,
)


class SecurityAnalysisAgent:
    """
    Specialist responsible for security-event analysis.

    Delegates execution to the existing
    InvestigationWorkflow rather than duplicating
    its tool selection or detection logic.
    """

    REQUIRED_PERMISSION = "security:read"
    MAX_EVENTS = 1000

    def __init__(
        self,
        *,
        client: Any,
        model: str,
    ):
        if client is None:
            raise ValueError(
                "An AI client is required"
            )

        if not isinstance(model, str) or not model.strip():
            raise ValueError(
                "A valid model is required"
            )

        self.workflow = InvestigationWorkflow(
            client=client,
            model=model,
        )

    def run(
        self,
        *,
        request: str,
        events: list[dict],
        granted_permissions: set[str],
        investigation_id: str | None = None,
    ) -> dict:
        """
        Run authorized security analysis.

        The underlying workflow handles:
        - Bounded LLM tool selection
        - Approved security tool execution
        - Log analysis and statistics
        - Severity assessment
        - Evidence references to input events

        The agent does not independently execute
        tools or bypass the existing registry.
        """

        # Validate the investigation request.
        if not isinstance(request, str):
            raise ValueError(
                "Investigation request must be text"
            )

        if not 1 <= len(request.strip()) <= 2000:
            raise ValueError(
                "Request must contain 1-2000 characters"
            )

        # Validate security event collection.
        if not isinstance(events, list):
            raise ValueError(
                "Security events must be a list"
            )

        if len(events) > self.MAX_EVENTS:
            raise ValueError(
                "Maximum 1000 security events allowed"
            )

        if not all(
            isinstance(event, dict)
            for event in events
        ):
            raise ValueError(
                "Each security event must be an object"
            )

        # Enforce permissions before any model call.
        if not isinstance(granted_permissions, set):
            raise PermissionError(
                "Invalid security permissions"
            )

        if (
            self.REQUIRED_PERMISSION
            not in granted_permissions
        ):
            raise PermissionError(
                "Missing security:read permission"
            )

        # Delegate to the existing, tested workflow.
        # Do not introduce a second tool registry.
        result = self.workflow.run(
            request=request,
            events=events,
            granted_permissions=granted_permissions,
            investigation_id=investigation_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid security analysis result"
            )

        # Validate the existing workflow contract.
        returned_id = result.get("investigation_id")

        if (
            not isinstance(returned_id, str)
            or not returned_id
        ):
            raise RuntimeError(
                "Security analysis returned no investigation ID"
            )

        if (
            investigation_id is not None
            and returned_id != investigation_id
        ):
            raise RuntimeError(
                "INVESTIGATION_ID_MISMATCH"
            )

        status = result.get("status")

        if status not in {
            "completed",
            "no_tool_selected",
        }:
            raise RuntimeError(
                "Unexpected security analysis status"
            )

        if status == "completed":
            if not isinstance(
                result.get("report"),
                dict,
            ):
                raise RuntimeError(
                    "Security analysis report is missing"
                )

            if not isinstance(
                result.get("steps"),
                list,
            ):
                raise RuntimeError(
                    "Security analysis steps are invalid"
                )

        return result
