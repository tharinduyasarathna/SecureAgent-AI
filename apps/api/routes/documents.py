
from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pypdf import PdfReader
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

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_TEXT_CHARACTERS = 100_000
MAX_CHUNKS = 100

ALLOWED_EXTENSIONS = {".txt", ".pdf"}


def extract_pdf_text(raw_content: bytes) -> str:
    if not raw_content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file",
        )

    try:
        reader = PdfReader(
            BytesIO(raw_content),
            strict=True,
        )

        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Encrypted PDFs are not supported",
            )

        if len(reader.pages) > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"PDF exceeds the {MAX_PDF_PAGES}-page limit"
                ),
            )

        extracted_pages = []
        total_characters = 0

        for page in reader.pages:
            page_text = page.extract_text() or ""

            total_characters += len(page_text)

            if total_characters > MAX_TEXT_CHARACTERS:
                raise HTTPException(
                    status_code=413,
                    detail="PDF contains too much text",
                )

            if page_text.strip():
                extracted_pages.append(page_text)

        return "\n\n".join(extracted_pages)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read PDF document",
        ) from None


def extract_txt_text(raw_content: bytes) -> str:
    try:
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Text file must contain UTF-8 text",
        ) from None

    if len(text) > MAX_TEXT_CHARACTERS:
        raise HTTPException(
            status_code=413,
            detail="Document contains too much text",
        )

    return text


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = Path(
        (file.filename or "").replace("\\", "/")
    ).name

    if not filename or filename in {".", ".."}:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    if len(filename) > 255:
        raise HTTPException(
            status_code=400,
            detail="Filename is too long",
        )

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .txt and .pdf files are supported",
        )

    try:
        raw_content = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    if len(raw_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 5 MB limit",
        )

    if not raw_content:
        raise HTTPException(
            status_code=400,
            detail="Document is empty",
        )

    if extension == ".pdf":
        text = extract_pdf_text(raw_content)
    else:
        text = extract_txt_text(raw_content)

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Document contains no extractable text"
            ),
        )

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
        "file_type": extension.removeprefix("."),
        "chunks_created": len(chunks),
        "embedding_dimensions": 1536,
        "status": "indexed",
    }
