
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from apps.api.agents.secure_investigation import (
    SecureInvestigationWorkflow,
)


@pytest.fixture
def setup_secure_workflow():
    audit = Mock()
    investigation_id = str(uuid4())

    workflow = SecureInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
        audit_service=audit,
    )

    workflow.audited_workflow.run = AsyncMock(
        return_value={
            "investigation_id": investigation_id,
            "status": "completed",
            "steps": [],
            "report": {
                "severity": "medium",
            },
            "evidence": {
                "sources": [
                    {
                        "source": "document",
                        "document_id": 1,
                        "chunk_id": 10,
                        "filename": "incident.txt",
                        "similarity": 0.95,
                        "content": "Six failed logins detected.",
                    },
                ],
            },
        }
    )

    return workflow, audit, investigation_id


def run_args():
    return {
        "db": Mock(),
        "user_id": 2,
        "request": "Investigate failed logins",
        "events": [],
        "granted_permissions": {"security:read"},
    }


@pytest.mark.asyncio
async def test_synthesis_success_audited(
    setup_secure_workflow,
):
    workflow, audit, investigation_id = (
        setup_secure_workflow
    )

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        return_value={
            "summary": "Suspicious login activity.",
            "risk_level": "medium",
            "source_ids": [10],
            "limitations": [],
        },
    ):
        result = await workflow.run(**run_args())

    assert result["synthesis_status"] == "completed"

    audit.record_event.assert_called_once_with(
        investigation_id=investigation_id,
        event_type="evidence_synthesis",
        status="completed",
        details={},
    )

    audit.finish_investigation.assert_called_once_with(
        investigation_id=investigation_id,
        status="completed",
        severity="medium",
    )

    assert (
        workflow.audited_workflow.run.call_args.kwargs[
            "finalize"
        ]
        is False
    )


@pytest.mark.asyncio
async def test_synthesis_failure_audited(
    setup_secure_workflow,
):
    workflow, audit, investigation_id = (
        setup_secure_workflow
    )

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        side_effect=RuntimeError("Sensitive model error"),
    ):
        result = await workflow.run(**run_args())

    assert result["synthesis_status"] == "failed"
    assert result["evidence_synthesis"] is None

    audit.record_event.assert_called_once_with(
        investigation_id=investigation_id,
        event_type="evidence_synthesis",
        status="failed",
        details={
            "error_code": "SYNTHESIS_FAILED",
        },
    )

    audit.finish_investigation.assert_called_once_with(
        investigation_id=investigation_id,
        status="failed",
        error_code="SYNTHESIS_FAILED",
    )


@pytest.mark.asyncio
async def test_incomplete_investigation_skips_synthesis(
    setup_secure_workflow,
):
    workflow, audit, _ = setup_secure_workflow

    workflow.audited_workflow.run.return_value = {
        "investigation_id": str(uuid4()),
        "status": "no_tool_selected",
        "steps": [],
        "report": None,
        "evidence": {
            "sources": [],
        },
    }

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence"
    ) as synthesis:
        result = await workflow.run(**run_args())

    assert result["synthesis_status"] == "skipped"
    synthesis.assert_not_called()

    # Underlying workflow handles finalization.
    audit.record_event.assert_not_called()
    audit.finish_investigation.assert_not_called()


@pytest.mark.asyncio
async def test_audit_failure_is_not_silenced(
    setup_secure_workflow,
):
    workflow, audit, _ = setup_secure_workflow

    audit.record_event.side_effect = RuntimeError(
        "Audit database unavailable"
    )

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        return_value={
            "summary": "Suspicious login activity.",
            "risk_level": "medium",
            "source_ids": [10],
            "limitations": [],
        },
    ):
        with pytest.raises(
            RuntimeError,
            match="Audit database unavailable",
        ):
            await workflow.run(**run_args())

    audit.finish_investigation.assert_not_called()
