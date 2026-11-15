
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.rag.retriever import retrieve_chunks


router = APIRouter(
    prefix="/rag",
    tags=["RAG Search"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/search")
async def search_documents(
    request: SearchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.query.strip():
        raise HTTPException(
            status_code=422,
            detail="Query cannot be empty",
        )

    results = await retrieve_chunks(
        db=db,
        user_id=user.id,
        query=request.query,
        top_k=request.top_k,
    )

    return {
        "query": request.query,
        "results_count": len(results),
        "results": results,
    }
