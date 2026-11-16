
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.api.agents.evidence_workflow import (
    EvidenceInvestigationWorkflow,
)
from apps.api.agents.rag_evidence import (
    EvidenceRetrievalError,
    retrieve_investigation_evidence,
)


def make_client(tool_name="analyze_security_logs"):
    client = Mock()
    client.responses.create.return_value = (
        SimpleNamespace(
            output_text=json.dumps({
                "tool_name": tool_name
            })
        )
    )
    return client


def make_events():
    return [
        {
            "timestamp": "2026-11-16T12:00:00Z",
            "event_type": "login_failure",
            "source_ip": "192.0.2.10",
        }
        for _ in range(6)
    ]


def sample_chunks():
    return [{
        "chunk_id": 21,
        "document_id": 10,
        "filename": "incident_report.txt",
        "chunk_index": 0,
        "similarity": 0.91,
        "content": (
            "Incident SEC-2026-301 involved "
            "repeated authentication failures."
        ),
    }]


@pytest.mark.asyncio
async def test_evidence_adapter():
    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mocked:
        mocked.return_value = sample_chunks()

        result = await retrieve_investigation_evidence(
            db=Mock(),
            user_id=1,
            query="Investigate authentication failures",
        )

        assert result["results_count"] == 1
        assert result["sources"][0]["document_id"] == 10
        assert result["sources"][0]["chunk_id"] == 21

        assert mocked.await_args.kwargs["user_id"] == 1


@pytest.mark.asyncio
async def test_invalid_user_rejected():
    with pytest.raises(EvidenceRetrievalError):
        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=0,
            query="Investigate logs",
        )


@pytest.mark.asyncio
async def test_invalid_top_k_rejected():
    with pytest.raises(EvidenceRetrievalError):
        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=1,
            query="Investigate logs",
            top_k=100,
        )


@pytest.mark.asyncio
async def test_invalid_document_id_rejected():
    with pytest.raises(EvidenceRetrievalError):
        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=1,
            query="Investigate logs",
            document_id=-1,
        )


@pytest.mark.asyncio
async def test_evidence_workflow_success():
    workflow = EvidenceInvestigationWorkflow(
        client=make_client(),
        model="mock-model",
    )

    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mocked:
        mocked.return_value = sample_chunks()

        result = await workflow.run(
            db=Mock(),
            user_id=1,
            request="Investigate failed logins",
            events=make_events(),
            granted_permissions={"security:read"},
        )

        assert result["status"] == "completed"
        assert len(result["steps"]) == 2
        assert result["evidence"]["results_count"] == 1
        assert (
            result["report"]["evidence_status"]
            == "retrieved"
        )


@pytest.mark.asyncio
async def test_permission_denied_before_retrieval():
    client = make_client()

    workflow = EvidenceInvestigationWorkflow(
        client=client,
        model="mock-model",
    )

    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mocked:
        with pytest.raises(PermissionError):
            await workflow.run(
                db=Mock(),
                user_id=1,
                request="Investigate logs",
                events=make_events(),
                granted_permissions=set(),
            )

        mocked.assert_not_awaited()
        client.responses.create.assert_not_called()


@pytest.mark.asyncio
async def test_no_tool_means_no_retrieval():
    workflow = EvidenceInvestigationWorkflow(
        client=make_client("none"),
        model="mock-model",
    )

    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mocked:
        result = await workflow.run(
            db=Mock(),
            user_id=1,
            request="Write a poem",
            events=[],
            granted_permissions={"security:read"},
        )

        assert result["status"] == "no_tool_selected"
        mocked.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_filter_forwarded():
    with patch(
        "apps.api.agents.rag_evidence.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mocked:
        mocked.return_value = []

        await retrieve_investigation_evidence(
            db=Mock(),
            user_id=7,
            query="Find incident report",
            document_id=25,
        )

        assert mocked.await_args.kwargs["user_id"] == 7
        assert mocked.await_args.kwargs["document_id"] == 25
