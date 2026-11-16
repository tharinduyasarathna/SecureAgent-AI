
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.rag.embeddings import generate_embedding
from apps.api.rag.models import RAGChunk, RAGDocument


async def retrieve_chunks(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 5,
    document_id: int | None = None,
) -> list[dict]:
    """
    Retrieve semantically similar document chunks
    belonging to the authenticated user.
    """

    if not query.strip():
        raise ValueError("Query cannot be empty")

    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")

    query_embedding = await generate_embedding(query)

    distance = RAGChunk.embedding.cosine_distance(
        query_embedding
    )

    distance = RAGChunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            RAGChunk.id,
            RAGChunk.content,
            RAGChunk.chunk_index,
            RAGDocument.id.label("document_id"),
            RAGDocument.filename,
            distance.label("distance"),
        )
        .join(
            RAGDocument,
            RAGChunk.document_id == RAGDocument.id,
        )
        .where(RAGDocument.owner_id == user_id)
    )

    if document_id is not None:
        statement = statement.where(
            RAGDocument.id == document_id
        )

    statement = (
        statement
        .order_by(distance)
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    return [
        {
            "chunk_id": row.id,
            "document_id": row.document_id,
            "filename": row.filename,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "similarity": round(
                1.0 - float(row.distance),
                4,
            ),
        }
        for row in rows
    ]
