
from apps.api.agents.supervisor_agent import (
    SupervisorAgent,
)


class SecureInvestigationWorkflow(SupervisorAgent):
    """
    Compatibility entry point for the existing API.

    Inherits:
    - Constructor configuration
    - Security authorization
    - Audited investigation execution
    - Evidence synthesis
    - Structured report generation

    No changes are required to the existing
    /investigations endpoint.
    """

    pass
