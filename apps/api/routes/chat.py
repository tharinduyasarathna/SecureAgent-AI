
import logging

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError, APITimeoutError
from pydantic import BaseModel, Field

from apps.api.agents.llm_service import OpenAILLMService
from apps.api.app.auth_dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["AI Chat"],
    dependencies=[Depends(get_current_user)],
)


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
        description="Question to send to SecureAgent AI",
    )


class ChatResponse(BaseModel):
    answer: str


def get_llm_service():
    return OpenAILLMService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm: OpenAILLMService = Depends(get_llm_service),
):
    try:
        answer = await llm.ask(request.question)

        return ChatResponse(answer=answer)

    except ValueError:
        logger.exception("LLM configuration error")
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured",
        ) from None

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out",
        ) from None

    except APIError:
        logger.exception("OpenAI API request failed")
        raise HTTPException(
            status_code=502,
            detail="AI provider request failed",
        ) from None
