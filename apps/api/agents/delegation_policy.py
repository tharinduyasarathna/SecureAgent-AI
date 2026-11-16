
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentPermission:
    name: str
    required_permissions: frozenset[str]
    max_executions: int = 1


AGENT_PERMISSIONS = {
    "security_analysis": AgentPermission(
        name="security_analysis",
        required_permissions=frozenset({"security:read"}),
    ),
    "rag_knowledge": AgentPermission(
        name="rag_knowledge",
        required_permissions=frozenset({"security:read"}),
    ),
    "report_generation": AgentPermission(
        name="report_generation",
        required_permissions=frozenset({"security:read"}),
    ),
}


@dataclass
class DelegationContext:
    user_id: int
    investigation_id: str
    granted_permissions: set[str]
    execution_counts: dict[str, int] = field(
        default_factory=dict
    )


class DelegationPolicy:
    def __init__(self):
        self.allowed_agents = AGENT_PERMISSIONS

    def authorize(
        self,
        *,
        agent_name: str,
        context: DelegationContext,
    ) -> None:
        if agent_name not in self.allowed_agents:
            raise PermissionError(
                "Unauthorized specialist agent"
            )

        if type(context.user_id) is not int or context.user_id <= 0:
            raise ValueError("Invalid authenticated user")

        if (
            not isinstance(context.investigation_id, str)
            or not context.investigation_id.strip()
        ):
            raise ValueError("Invalid investigation ID")

        if not isinstance(context.granted_permissions, set):
            raise PermissionError("Invalid permissions")

        agent = self.allowed_agents[agent_name]

        if not agent.required_permissions.issubset(
            context.granted_permissions
        ):
            raise PermissionError(
                "Missing required agent permissions"
            )

        execution_count = context.execution_counts.get(
            agent_name, 0
        )

        if execution_count >= agent.max_executions:
            raise PermissionError(
                "Agent execution limit exceeded"
            )

    def record_execution(
        self,
        *,
        agent_name: str,
        context: DelegationContext,
    ) -> None:
        self.authorize(
            agent_name=agent_name,
            context=context,
        )

        context.execution_counts[agent_name] = (
            context.execution_counts.get(agent_name, 0) + 1
        )

    def get_execution_summary(
        self,
        *,
        context: DelegationContext,
    ) -> dict:
        return {
            "investigation_id": context.investigation_id,
            "user_id": context.user_id,
            "agent_executions": dict(
                context.execution_counts
            ),
            "total_executions": sum(
                context.execution_counts.values()
            ),
        }
