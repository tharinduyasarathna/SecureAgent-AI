
from typing import Any

from sqlalchemy.orm import Session

from apps.api.rag.retriever import retrieve_chunks


class EvidenceRetrievalError(Exception):
    """Raised when evidence retrieval is invalid."""


async def retrieve_investigation_evidence(
    *,
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 5,
    document_id: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve evidence owned by the authenticated user.

    user_id must come from trusted JWT authentication.
    Never accept user_id from LLM-generated arguments.
    """

    if type(user_id) is not int or user_id <= 0:
        raise EvidenceRetrievalError(
            "Invalid authenticated user"
        )

    if not isinstance(query, str):
        raise EvidenceRetrievalError(
            "Evidence query must be text"
        )

    if not query.strip() or len(query) > 2000:
        raise EvidenceRetrievalError(
            "Evidence query must contain 1-2000 characters"
        )

    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise EvidenceRetrievalError(
            "top_k must be between 1 and 10"
        )

    if document_id is not None and (
        type(document_id) is not int or document_id <= 0
    ):
        raise EvidenceRetrievalError(
            "Invalid document ID"
        )

    results = await retrieve_chunks(
        db=db,
        user_id=user_id,
        query=query,
        top_k=top_k,
        document_id=document_id,
    )

    sources = []

    for index, result in enumerate(results, start=1):
        sources.append({
            "source": f"Source {index}",
            "document_id": result["document_id"],
            "chunk_id": result["chunk_id"],
            "filename": result["filename"],
            "chunk_index": result["chunk_index"],
            "similarity": result["similarity"],
            "content": result["content"],
        })

    return {
        "query": query,
        "results_count": len(sources),
        "sources": sources,
    }
