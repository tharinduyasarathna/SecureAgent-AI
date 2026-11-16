
from dataclasses import dataclass
from typing import Any, Callable


class ToolSecurityError(Exception):
    """Raised when an agent tool action is not permitted."""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., Any]
    permission: str
    read_only: bool = True


class SecureToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        if not tool.read_only:
            raise ToolSecurityError(
                "Only read-only tools are allowed in Phase 4.1"
            )

        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission": tool.permission,
                "read_only": tool.read_only,
            }
            for tool in self._tools.values()
        ]

    def execute(
        self,
        tool_name: str,
        *,
        granted_permissions: set[str],
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        tool = self._tools.get(tool_name)

        if tool is None:
            raise ToolSecurityError(
                f"Unknown or unauthorized tool: {tool_name}"
            )

        if tool.permission not in granted_permissions:
            raise ToolSecurityError(
                f"Missing permission: {tool.permission}"
            )

        if not tool.read_only:
            raise ToolSecurityError(
                "Write operations are not permitted"
            )

        return tool.handler(**(arguments or {}))
