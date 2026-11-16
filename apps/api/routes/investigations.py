
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.agents.audit_service import AuditService
from apps.api.agents.secure_investigation import (
    SecureInvestigationWorkflow,
)
from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations",
    tags=["Security Investigations"],
)


# ============================================================
# Request Schema
# ============================================================

class InvestigationRequest(BaseModel):
    request: str = Field(
        min_length=1,
        max_length=2000,
        description="Security investigation instructions",
    )

    events: list[dict] = Field(
        default_factory=list,
        max_length=1000,
        description="Security events to investigate",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Maximum number of RAG evidence results",
    )

    document_id: int | None = Field(
        default=None,
        ge=1,
        description="Optional document ID for scoped retrieval",
    )


# ============================================================
# Authorization
# ============================================================

def get_investigation_permissions(
    user: User = Depends(get_current_user),
) -> set[str]:
    """
    Initial single-role application policy.

    Authenticated users may investigate submitted security
    events and retrieve their own RAG documents.

    Replace this with role-based authorization when
    introducing multiple privilege levels.
    """
    return {"security:read"}


# ============================================================
# Workflow Dependency
# ============================================================

def get_investigation_workflow():
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")

    if not api_key or not model:
        logger.error(
            "Investigation AI configuration missing"
        )

        raise HTTPException(
            status_code=503,
            detail="AI service is not configured",
        )

    client = OpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=2,
    )

    return SecureInvestigationWorkflow(
        client=client,
        model=model,
    )


# ============================================================
# Create Investigation
# ============================================================

@router.post("")
async def create_investigation(
    payload: InvestigationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    permissions: set[str] = Depends(
        get_investigation_permissions
    ),
    workflow: SecureInvestigationWorkflow = Depends(
        get_investigation_workflow
    ),
):
    """
    Execute an AI-powered security investigation.

    Steps:
    1. Authenticate the user.
    2. Apply server-side security permissions.
    3. Run the secure investigation workflow.
    4. Execute approved security tools and RAG retrieval.
    5. Synthesize evidence.
    6. Return investigation findings and audit metadata.
    """

    if not payload.request.strip():
        raise HTTPException(
            status_code=422,
            detail="Investigation request cannot be empty",
        )

    logger.info(
        "Starting security investigation for user_id=%s",
        user.id,
    )

    try:
        result = await workflow.run(
            db=db,
            user_id=user.id,
            request=payload.request,
            events=payload.events,
            granted_permissions=permissions,
            top_k=payload.top_k,
            document_id=payload.document_id,
        )

        logger.info(
            "Investigation finished: id=%s status=%s",
            result.get("investigation_id"),
            result.get("status"),
        )

        return result

    except PermissionError:
        logger.warning(
            "Investigation authorization denied for user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=403,
            detail="Investigation access denied",
        ) from None

    except ValueError:
        logger.exception(
            "Investigation validation failed for user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=422,
            detail="Invalid investigation input",
        ) from None

    except Exception:
        logger.exception(
            "Security investigation failed for user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Investigation could not be completed",
        ) from None


# ============================================================
# Investigation History
# ============================================================

@router.get("/{investigation_id}")
def get_investigation_history(
    investigation_id: str,
    user: User = Depends(get_current_user),
):
    """
    Retrieve the audit history of an investigation
    belonging to the authenticated user.
    """

    try:
        canonical_id = str(UUID(investigation_id))

        if canonical_id != investigation_id:
            raise ValueError("Noncanonical UUID")

    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation ID",
        ) from None

    try:
        history = AuditService().get_history(
            investigation_id=canonical_id,
            user_id=user.id,
        )

    except Exception:
        logger.exception(
            "Failed to retrieve investigation history"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve investigation history",
        ) from None

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    return history
