
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.rag.rag_service import answer_with_rag


router = APIRouter(
    prefix="/rag",
    tags=["RAG Chat"],
)


class RAGQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    document_id: int | None = Field(
        default=None,
        ge=1,
    )


@router.post("/ask")
async def ask_rag(
    request: RAGQuestion,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.question.strip():
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty",
        )

    return await answer_with_rag(
        db=db,
        user_id=user.id,
        question=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
    )
