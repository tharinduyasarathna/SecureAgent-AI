
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.rag.chunker import chunk_text
from apps.api.rag.embeddings import generate_embedding
from apps.api.rag.models import RAGChunk, RAGDocument


router = APIRouter(
    prefix="/rag/documents",
    tags=["RAG Documents"],
)

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
MAX_CHUNKS = 100


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a text document, generate embeddings,
    and store its chunks in PostgreSQL.
    """

    filename = Path(
        (file.filename or "").replace("\\", "/")
    ).name

    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported",
        )

    if len(filename) > 255:
        raise HTTPException(
            status_code=400,
            detail="Filename is too long",
        )

    # Read at most 1 MB plus one byte.
    # This prevents unlimited uploads.
    try:
        raw_content = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    if len(raw_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 1 MB limit",
        )

    try:
        text = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must contain UTF-8 text",
        ) from None

    chunks = chunk_text(
        text,
        chunk_size=1000,
        overlap=150,
    )

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="Document is empty",
        )

    if len(chunks) > MAX_CHUNKS:
        raise HTTPException(
            status_code=413,
            detail="Document contains too many chunks",
        )

    # Generate embeddings before creating database rows.
    # This avoids holding a database transaction open
    # while waiting for OpenAI.
    try:
        embeddings = []

        for chunk in chunks:
            embedding = await generate_embedding(chunk)
            embeddings.append(embedding)

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Embedding generation failed",
        ) from None

    document = RAGDocument(
        owner_id=user.id,
        filename=filename,
    )

    try:
        db.add(document)
        db.flush()

        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            db.add(
                RAGChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=embedding,
                )
            )

        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()
        raise

    return {
        "document_id": document.id,
        "filename": document.filename,
        "owner_id": document.owner_id,
        "chunks_created": len(chunks),
        "embedding_dimensions": 1536,
        "status": "indexed",
    }
