
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.api.agents.secure_investigation import (
    SecureInvestigationWorkflow,
)


def sample_result():
    return {
        "investigation_id": "synthetic-id",
        "status": "completed",
        "steps": [],
        "report": {
            "severity": "medium",
            "summary": "Repeated failed logins detected.",
        },
        "evidence": {
            "sources": [
                {
                    "chunk_id": 10,
                    "content": (
                        "Six failed login attempts."
                    ),
                }
            ]
        },
    }


def sample_synthesis():
    return {
        "summary": "Repeated failed logins.",
        "risk_level": "medium",
        "source_ids": [10],
        "limitations": "No successful login confirmed.",
    }


@pytest.fixture
def workflow():
    instance = SecureInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
        audit_service=Mock(),
    )

    instance.audited_workflow.run = AsyncMock(
        return_value=sample_result()
    )

    return instance


def run_args():
    return {
        "db": Mock(),
        "user_id": 2,
        "request": "Investigate failed logins",
        "events": [],
        "granted_permissions": {"security:read"},
    }


@pytest.mark.asyncio
async def test_synthesis_integrated(workflow):
    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        return_value=sample_synthesis(),
    ):
        result = await workflow.run(**run_args())

    assert result["synthesis_status"] == "completed"
    assert result["evidence_synthesis"]["source_ids"] == [10]


@pytest.mark.asyncio
async def test_original_report_preserved(workflow):
    original = sample_result()["report"].copy()

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        return_value=sample_synthesis(),
    ):
        result = await workflow.run(**run_args())

    assert result["report"] == original


@pytest.mark.asyncio
async def test_synthesis_failure_is_reported(workflow):
    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence",
        side_effect=RuntimeError(
            "Synthetic model failure"
        ),
    ):
        result = await workflow.run(**run_args())

    assert result["synthesis_status"] == "failed"
    assert result["evidence_synthesis"] is None


@pytest.mark.asyncio
async def test_incomplete_investigation_skips_synthesis(
    workflow,
):
    result = sample_result()
    result["status"] = "no_tool_selected"

    workflow.audited_workflow.run.return_value = result

    with patch(
        "apps.api.agents.secure_investigation."
        "synthesize_evidence"
    ) as synthesis:
        output = await workflow.run(**run_args())

    synthesis.assert_not_called()
    assert output["synthesis_status"] == "skipped"


@pytest.mark.asyncio
async def test_underlying_permission_denial_propagates(
    workflow,
):
    workflow.audited_workflow.run.side_effect = (
        PermissionError("Access denied")
    )

    with pytest.raises(PermissionError):
        await workflow.run(**run_args())



@pytest.mark.asyncio
async def test_successful_synthesis_finalizes_audit(workflow):
    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence",
        return_value=sample_synthesis(),
    ):
        result = await workflow.run(**run_args())

    audit = workflow.audited_workflow.audit

    assert result["status"] == "completed"
    assert result["synthesis_status"] == "completed"

    audit.record_event.assert_called_once_with(
        investigation_id="synthetic-id",
        event_type="evidence_synthesis",
        status="completed",
        details={},
    )

    audit.finish_investigation.assert_called_once_with(
        investigation_id="synthetic-id",
        status="completed",
        severity="medium",
    )


@pytest.mark.asyncio
async def test_synthesis_failure_finalizes_as_failed(workflow):
    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence",
        side_effect=RuntimeError("Synthetic LLM failure"),
    ):
        result = await workflow.run(**run_args())

    audit = workflow.audited_workflow.audit

    assert result["status"] == "failed"
    assert result["synthesis_status"] == "failed"
    assert result["evidence_synthesis"] is None

    audit.record_event.assert_called_once_with(
        investigation_id="synthetic-id",
        event_type="evidence_synthesis",
        status="failed",
        details={"error_code": "SYNTHESIS_FAILED"},
    )

    audit.finish_investigation.assert_called_once_with(
        investigation_id="synthetic-id",
        status="failed",
        error_code="SYNTHESIS_FAILED",
    )


@pytest.mark.asyncio
async def test_audit_record_failure_does_not_report_success(
    workflow,
):
    audit = workflow.audited_workflow.audit
    audit.record_event.side_effect = RuntimeError(
        "Synthetic audit database failure"
    )

    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence",
        return_value=sample_synthesis(),
    ):
        with pytest.raises(
            RuntimeError,
            match="Synthetic audit database failure",
        ):
            await workflow.run(**run_args())

    audit.finish_investigation.assert_not_called()


@pytest.mark.asyncio
async def test_audit_finalization_failure_does_not_report_success(
    workflow,
):
    audit = workflow.audited_workflow.audit
    audit.finish_investigation.side_effect = RuntimeError(
        "Synthetic finalization failure"
    )

    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence",
        return_value=sample_synthesis(),
    ):
        with pytest.raises(
            RuntimeError,
            match="Synthetic finalization failure",
        ):
            await workflow.run(**run_args())

    audit.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_incomplete_investigation_does_not_finalize_twice(
    workflow,
):
    result = sample_result()
    result["status"] = "no_tool_selected"

    workflow.audited_workflow.run.return_value = result

    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence"
    ) as synthesis:
        output = await workflow.run(**run_args())

    assert output["synthesis_status"] == "skipped"

    synthesis.assert_not_called()

    audit = workflow.audited_workflow.audit
    audit.record_event.assert_not_called()
    audit.finish_investigation.assert_not_called()


@pytest.mark.asyncio
async def test_synthesis_failure_does_not_expose_raw_error(
    workflow,
):
    secret = "SYNTHETIC_PRIVATE_API_KEY"

    with patch(
        "apps.api.agents.secure_investigation.synthesize_evidence",
        side_effect=RuntimeError(secret),
    ):
        result = await workflow.run(**run_args())

    assert result["status"] == "failed"
    assert result["synthesis_status"] == "failed"
    assert secret not in str(result)

    audit = workflow.audited_workflow.audit

    assert secret not in str(audit.record_event.call_args)
    assert secret not in str(audit.finish_investigation.call_args)
