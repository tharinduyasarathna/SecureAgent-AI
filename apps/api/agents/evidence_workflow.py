
from typing import Any

from sqlalchemy.orm import Session

from apps.api.agents.investigation_workflow import (
    InvestigationWorkflow,
)
from apps.api.agents.rag_evidence import (
    retrieve_investigation_evidence,
)


class EvidenceInvestigationWorkflow:
    """
    Combine deterministic security-log findings
    with authenticated, owner-scoped RAG evidence.
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
    ):
        self.investigation = InvestigationWorkflow(
            client=client,
            model=model,
        )

    async def run(
        self,
        *,
        db: Session,
        user_id: int,
        request: str,
        events: list[dict],
        granted_permissions: set[str],
        top_k: int = 5,
        document_id: int | None = None,
        investigation_id: str | None = None,
    ) -> dict:
        # Validate identity and authorization before
        # either the LLM or the retrieval service runs.
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid authenticated user")

        if (
            not isinstance(granted_permissions, set)
            or "security:read" not in granted_permissions
        ):
            raise PermissionError(
                "Missing security:read permission"
            )

        if not isinstance(request, str):
            raise ValueError("Invalid investigation request")

        if not request.strip() or len(request) > 2000:
            raise ValueError(
                "Request must contain 1-2000 characters"
            )

        if type(top_k) is not int or not 1 <= top_k <= 10:
            raise ValueError("Invalid top_k")

        if document_id is not None and (
            type(document_id) is not int
            or document_id <= 0
        ):
            raise ValueError("Invalid document_id")

        investigation = self.investigation.run(
            request=request,
            events=events,
            granted_permissions=granted_permissions,
            investigation_id=investigation_id,
        )

        if investigation["status"] != "completed":
            return {
                **investigation,
                "evidence": {
                    "results_count": 0,
                    "sources": [],
                },
            }

        evidence = await retrieve_investigation_evidence(
            db=db,
            user_id=user_id,
            query=request,
            top_k=top_k,
            document_id=document_id,
        )

        report = dict(investigation["report"])

        report["evidence_references"] = [
            {
                "source": source["source"],
                "document_id": source["document_id"],
                "chunk_id": source["chunk_id"],
                "filename": source["filename"],
                "similarity": source["similarity"],
            }
            for source in evidence["sources"]
        ]

        report["evidence_status"] = (
            "retrieved"
            if evidence["results_count"] > 0
            else "no_documents_found"
        )

        return {
            **investigation,
            "report": report,
            "evidence": evidence,
        }
