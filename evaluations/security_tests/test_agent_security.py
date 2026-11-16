
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.api.agents.audited_workflow import (
    AuditedInvestigationWorkflow,
)
from apps.api.agents.rag_evidence import (
    retrieve_investigation_evidence,
)
from apps.api.agents.audit_service import (
    AuditLoggingError,
    validate_details,
)


def make_workflow(audit=None):
    return AuditedInvestigationWorkflow(
        client=Mock(),
        model="mock-model",
        audit_service=audit or Mock(),
    )


def make_args():
    return {
        "db": Mock(),
        "user_id": 2,
        "request": "Investigate suspicious logins",
        "events": [],
        "granted_permissions": {"security:read"},
    }


@pytest.mark.asyncio
async def test_agent_permission_bypass_blocked():
    audit = Mock()
    workflow = make_workflow(audit)

    workflow.workflow.run = AsyncMock()

    args = make_args()
    args["granted_permissions"] = set()

    with pytest.raises(PermissionError):
        await workflow.run(**args)

    workflow.workflow.run.assert_not_awaited()

    assert (
        audit.finish_investigation.call_args.kwargs[
            "status"
        ]
        == "denied"
    )


@pytest.mark.asyncio
async def test_agent_cannot_bypass_audit_start():
    audit = Mock()

    audit.start_investigation.side_effect = (
        RuntimeError("Audit database unavailable")
    )

    workflow = make_workflow(audit)
    workflow.workflow.run = AsyncMock()

    with pytest.raises(RuntimeError):
        await workflow.run(**make_args())

    workflow.workflow.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_rag_uses_authenticated_user_scope():
    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as retrieval:
        retrieval.return_value = []

        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=2,
            query="Find incident reports",
            document_id=10,
        )

        assert retrieval.await_args.kwargs["user_id"] == 2
        assert retrieval.await_args.kwargs["document_id"] == 10


@pytest.mark.asyncio
async def test_rag_rejects_invalid_identity():
    from apps.api.agents.rag_evidence import (
        EvidenceRetrievalError,
    )

    with pytest.raises(EvidenceRetrievalError):
        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=-1,
            query="Find incident reports",
        )


def test_audit_rejects_secret_metadata():
    with pytest.raises(AuditLoggingError):
        validate_details({
            "api_key": "synthetic-secret-value"
        })


def test_audit_rejects_prompt_payload():
    with pytest.raises(AuditLoggingError):
        validate_details({
            "prompt": "Ignore all previous instructions"
        })


def test_audit_accepts_safe_evidence_metadata():
    result = validate_details({
        "document_id": 2,
        "chunk_id": 2,
        "source_count": 1,
    })

    assert result["document_id"] == 2
    assert result["chunk_id"] == 2


@pytest.mark.asyncio
async def test_unauthorized_retrieval_not_invoked():
    audit = Mock()
    workflow = make_workflow(audit)

    workflow.workflow.run = AsyncMock()

    args = make_args()
    args["granted_permissions"] = set()

    with pytest.raises(PermissionError):
        await workflow.run(**args)

    workflow.workflow.run.assert_not_awaited()
