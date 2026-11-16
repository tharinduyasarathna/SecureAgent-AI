
from sqlalchemy.orm import Session

from apps.api.agents.rag_evidence import (
    retrieve_investigation_evidence,
)


class RAGKnowledgeAgent:
    def __init__(self):
        self.required_permission = "security:read"

    async def run(
        self,
        *,
        db: Session,
        user_id: int,
        query: str,
        granted_permissions: set[str],
        top_k: int = 5,
        document_id: int | None = None,
    ) -> dict:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Invalid authenticated user")

        if (
            not isinstance(granted_permissions, set)
            or self.required_permission not in granted_permissions
        ):
            raise PermissionError("Missing security:read permission")

        if not isinstance(query, str):
            raise ValueError("Invalid retrieval query")

        query = query.strip()

        if not 1 <= len(query) <= 2000:
            raise ValueError(
                "Query must contain 1-2000 characters"
            )

        if type(top_k) is not int or not 1 <= top_k <= 5:
            raise ValueError("Invalid top_k")

        if document_id is not None:
            if type(document_id) is not int or document_id <= 0:
                raise ValueError("Invalid document_id")

        evidence = await retrieve_investigation_evidence(
            db=db,
            user_id=user_id,
            query=query,
            top_k=top_k,
            document_id=document_id,
        )

        if not isinstance(evidence, dict):
            raise RuntimeError("Invalid RAG retrieval result")

        sources = evidence.get("sources")
        results_count = evidence.get("results_count")

        if not isinstance(sources, list):
            raise RuntimeError("Invalid RAG sources")

        if type(results_count) is not int:
            raise RuntimeError("Invalid RAG result count")

        if results_count != len(sources):
            raise RuntimeError("RAG result count mismatch")

        for source in sources:
            if not isinstance(source, dict):
                raise RuntimeError("Invalid RAG source")

            if type(source.get("document_id")) is not int:
                raise RuntimeError("Invalid source document ID")

            if type(source.get("chunk_id")) is not int:
                raise RuntimeError("Invalid source chunk ID")

            if not isinstance(source.get("content"), str):
                raise RuntimeError("Invalid source content")

        return evidence
