
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from apps.api.agents.investigation_workflow import (
    InvestigationWorkflow,
)
from apps.api.agents.evidence_workflow import (
    EvidenceInvestigationWorkflow,
)


def test_investigation_uses_supplied_id():
    investigation_id = str(uuid4())

    workflow = InvestigationWorkflow(
        client=Mock(),
        model="mock-model",
    )

    with patch(
        "apps.api.agents.investigation_workflow."
        "select_security_tool",
        return_value="none",
    ):
        result = workflow.run(
            request="Investigate authentication events",
            events=[],
            granted_permissions={"security:read"},
            investigation_id=investigation_id,
        )

    assert result["investigation_id"] == investigation_id


def test_investigation_generates_id_when_missing():
    workflow = InvestigationWorkflow(
        client=Mock(),
        model="mock-model",
    )

    with patch(
        "apps.api.agents.investigation_workflow."
        "select_security_tool",
        return_value="none",
    ):
        result = workflow.run(
            request="Investigate authentication events",
            events=[],
            granted_permissions={"security:read"},
        )

    assert result["investigation_id"]
    assert str(uuid4()) != result["investigation_id"]


@pytest.mark.parametrize(
    "invalid_id",
    ["invalid-uuid", "", 123, None],
)
def test_invalid_supplied_id_rejected(invalid_id):
    if invalid_id is None:
        pytest.skip(
            "None intentionally generates a new UUID"
        )

    workflow = InvestigationWorkflow(
        client=Mock(),
        model="mock-model",
    )

    with pytest.raises(ValueError):
        workflow.run(
            request="Investigate authentication events",
            events=[],
            granted_permissions={"security:read"},
            investigation_id=invalid_id,
        )


@pytest.mark.asyncio
async def test_evidence_workflow_forwards_id():
    investigation_id = str(uuid4())

    workflow = EvidenceInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
    )

    workflow.investigation.run = Mock(
        return_value={
            "investigation_id": investigation_id,
            "status": "no_tool_selected",
            "steps": [],
            "report": None,
        }
    )

    result = await workflow.run(
        db=Mock(),
        user_id=2,
        request="Investigate authentication events",
        events=[],
        granted_permissions={"security:read"},
        investigation_id=investigation_id,
    )

    assert result["investigation_id"] == investigation_id

    assert (
        workflow.investigation.run.call_args.kwargs[
            "investigation_id"
        ]
        == investigation_id
    )
