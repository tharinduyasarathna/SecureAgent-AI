
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.agents.document_event_extractor import (
    DocumentEventExtractor,
)
from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.rag.models import RAGChunk, RAGDocument


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/documents",
    tags=["Document Event Extraction"],
)

CHUNK_OVERLAP = 150
MAX_EXTRACTION_CHARACTERS = 30000


def reconstruct_document_text(chunks: list[str]) -> str:
    if not chunks:
        return ""

    text = chunks[0]

    for chunk in chunks[1:]:
        overlap = min(CHUNK_OVERLAP, len(text), len(chunk))

        if overlap and text.endswith(chunk[:overlap]):
            text += chunk[overlap:]
        else:
            text += chunk

        if len(text) > MAX_EXTRACTION_CHARACTERS:
            raise HTTPException(
                status_code=413,
                detail="Document exceeds the event extraction limit",
            )

    return text


@router.post("/{document_id}/extract-events")
def extract_document_events(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if document_id < 1:
        raise HTTPException(
            status_code=422,
            detail="Invalid document ID",
        )

    document = db.scalar(
        select(RAGDocument).where(
            RAGDocument.id == document_id,
            RAGDocument.owner_id == user.id,
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    chunks = db.scalars(
        select(RAGChunk.content)
        .where(RAGChunk.document_id == document.id)
        .order_by(RAGChunk.chunk_index.asc())
    ).all()

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Document has no indexed text",
        )

    document_text = reconstruct_document_text(chunks)

    if not document_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Document contains no extractable text",
        )

    if len(document_text) > MAX_EXTRACTION_CHARACTERS:
        raise HTTPException(
            status_code=413,
            detail="Document exceeds the event extraction limit",
        )

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")

    if not api_key or not model:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured",
        )

    client = OpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=2,
    )

    extractor = DocumentEventExtractor(
        client=client,
        model=model,
    )

    try:
        result = extractor.extract(text=document_text)
    except ValueError:
        logger.exception(
            "Document event extraction validation failed"
        )
        raise HTTPException(
            status_code=422,
            detail="Unable to extract valid document events",
        ) from None
    except Exception:
        logger.exception(
            "Document event extraction failed"
        )
        raise HTTPException(
            status_code=502,
            detail="AI document extraction failed",
        ) from None
    finally:
        client.close()

    return {
        "document_id": document.id,
        "filename": document.filename,
        **result,
    }
