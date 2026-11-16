
from unittest.mock import AsyncMock, Mock

import pytest

from apps.api.agents.audited_workflow import (
    AuditedInvestigationWorkflow,
)


def make_result():
    return {
        "investigation_id": "internal-id",
        "status": "completed",
        "steps": [
            {
                "step": 1,
                "tool_name": "analyze_security_logs",
                "status": "completed",
            },
            {
                "step": 2,
                "tool_name": "summarize_log_statistics",
                "status": "completed",
            },
        ],
        "report": {
            "severity": "medium",
        },
        "evidence": {
            "sources": [
                {
                    "document_id": 1,
                    "chunk_id": 10,
                },
            ],
        },
    }


@pytest.fixture
def setup_workflow():
    audit = Mock()

    # Provide a valid audit-history structure for
    # workflow error-handling tests.
    audit.get_history.return_value = {
        "status": "started",
        "events": [],
    }

    workflow = AuditedInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
        audit_service=audit,
    )

    async def mock_workflow_run(**kwargs):
        result = make_result()

        # Return the authoritative ID supplied by
        # AuditedInvestigationWorkflow.
        result["investigation_id"] = kwargs[
            "investigation_id"
        ]

        return result

    workflow.workflow.run = AsyncMock(
        side_effect=mock_workflow_run
    )

    return workflow, audit


def run_args():
    return {
        "db": Mock(),
        "user_id": 2,
        "request": "Investigate failed logins",
        "events": [],
        "granted_permissions": {"security:read"},
    }


@pytest.mark.asyncio
async def test_successful_investigation(setup_workflow):
    workflow, audit = setup_workflow

    result = await workflow.run(**run_args())

    assert result["status"] == "completed"
    assert result["investigation_id"] != "internal-id"

    # The returned ID must match the audit ID.
    audit_id = (
        audit.start_investigation.call_args.kwargs[
            "investigation_id"
        ]
    )

    assert result["investigation_id"] == audit_id

    # The same ID must be forwarded to the
    # underlying evidence workflow.
    forwarded_id = (
        workflow.workflow.run.call_args.kwargs[
            "investigation_id"
        ]
    )

    assert forwarded_id == audit_id

    audit.start_investigation.assert_called_once()
    audit.finish_investigation.assert_called_once()

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "completed"
    )


@pytest.mark.asyncio
async def test_tools_are_audited(setup_workflow):
    workflow, audit = setup_workflow

    result = await workflow.run(**run_args())

    tool_events = [
        call
        for call in audit.record_event.call_args_list
        if call.kwargs["event_type"] == "tool_executed"
    ]

    assert len(tool_events) == 2

    assert tool_events[0].kwargs["tool_name"] == (
        "analyze_security_logs"
    )

    assert tool_events[1].kwargs["tool_name"] == (
        "summarize_log_statistics"
    )

    for call in tool_events:
        assert (
            call.kwargs["investigation_id"]
            == result["investigation_id"]
        )


@pytest.mark.asyncio
async def test_evidence_is_audited(setup_workflow):
    workflow, audit = setup_workflow

    result = await workflow.run(**run_args())

    evidence_events = [
        call
        for call in audit.record_event.call_args_list
        if call.kwargs["event_type"]
        == "evidence_retrieved"
    ]

    assert len(evidence_events) == 2

    assert evidence_events[0].kwargs["details"] == {
        "source_count": 1,
    }

    assert evidence_events[1].kwargs["details"] == {
        "document_id": 1,
        "chunk_id": 10,
    }

    for call in evidence_events:
        assert (
            call.kwargs["investigation_id"]
            == result["investigation_id"]
        )


@pytest.mark.asyncio
async def test_denied_permission(setup_workflow):
    workflow, audit = setup_workflow

    args = run_args()
    args["granted_permissions"] = set()

    with pytest.raises(PermissionError):
        await workflow.run(**args)

    # No LLM workflow execution should occur.
    workflow.workflow.run.assert_not_awaited()

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "denied"
    )

    assert (
        audit.finish_investigation.call_args.kwargs[
            "error_code"
        ]
        == "PERMISSION_DENIED"
    )


@pytest.mark.asyncio
async def test_workflow_failure(setup_workflow):
    workflow, audit = setup_workflow

    workflow.workflow.run.side_effect = RuntimeError(
        "Synthetic workflow failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic workflow failure",
    ):
        await workflow.run(**run_args())

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "failed"
    )

    assert (
        audit.finish_investigation.call_args.kwargs[
            "error_code"
        ]
        == "INVESTIGATION_FAILED"
    )


@pytest.mark.asyncio
async def test_audit_start_failure_blocks_execution(
    setup_workflow,
):
    workflow, audit = setup_workflow

    audit.start_investigation.side_effect = (
        RuntimeError("Audit database unavailable")
    )

    with pytest.raises(
        RuntimeError,
        match="Audit database unavailable",
    ):
        await workflow.run(**run_args())

    # Fail closed: the investigation must not run
    # when the initial audit record cannot be stored.
    workflow.workflow.run.assert_not_awaited()

    audit.finish_investigation.assert_not_called()


@pytest.mark.asyncio
async def test_incomplete_workflow_is_marked_failed(
    setup_workflow,
):
    workflow, audit = setup_workflow

    async def mock_incomplete_workflow(**kwargs):
        result = make_result()

        # Preserve the authoritative investigation ID.
        result["investigation_id"] = kwargs[
            "investigation_id"
        ]

        result["status"] = "no_tool_selected"
        result["steps"] = []
        result["report"] = None
        result["evidence"]["sources"] = []

        return result

    workflow.workflow.run = AsyncMock(
        side_effect=mock_incomplete_workflow
    )

    result = await workflow.run(**run_args())

    assert result["status"] == "no_tool_selected"

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "failed"
    )

    assert (
        audit.finish_investigation.call_args.kwargs[
            "error_code"
        ]
        == "WORKFLOW_NOT_COMPLETED"
    )


@pytest.mark.asyncio
async def test_investigation_id_mismatch_is_rejected(
    setup_workflow,
):
    workflow, audit = setup_workflow

    async def mock_mismatched_workflow(**kwargs):
        result = make_result()

        # Simulate a compromised or incorrectly
        # implemented downstream workflow.
        result["investigation_id"] = "incorrect-id"

        return result

    workflow.workflow.run = AsyncMock(
        side_effect=mock_mismatched_workflow
    )

    with pytest.raises(
        RuntimeError,
        match="INVESTIGATION_ID_MISMATCH",
    ):
        await workflow.run(**run_args())

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "failed"
    )

    assert (
        audit.finish_investigation.call_args.kwargs[
            "error_code"
        ]
        == "INVESTIGATION_FAILED"
    )

    # No tool or evidence events should be recorded
    # for a mismatched investigation ID.
    audit.record_event.assert_not_called()
