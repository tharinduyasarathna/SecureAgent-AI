
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.agents.audit_service import AuditService
from apps.api.agents.secure_investigation import (
    SecureInvestigationWorkflow,
)
from apps.api.agents.investigation_report_service import (
    InvestigationReportService,
)
from apps.api.agents import investigation_report_models

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations",
    tags=["Security Investigations"],
)


class InvestigationRequest(BaseModel):
    request: str = Field(
        min_length=1,
        max_length=2000,
    )

    events: list[dict] = Field(
        default_factory=list,
        max_length=1000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=5,
    )

    document_id: int | None = Field(
        default=None,
        ge=1,
    )


def get_investigation_permissions(
    user: User = Depends(get_current_user),
) -> set[str]:
    return {"security:read"}


def get_investigation_workflow():
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

    return SecureInvestigationWorkflow(
        client=client,
        model=model,
    )


def validate_investigation_id(investigation_id: str) -> str:
    try:
        canonical = str(UUID(investigation_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation ID",
        ) from None

    if canonical != investigation_id:
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation ID",
        )

    return canonical


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
    if not payload.request.strip():
        raise HTTPException(
            status_code=422,
            detail="Investigation request cannot be empty",
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

    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Investigation access denied",
        ) from None

    except ValueError:
        logger.exception("Invalid investigation input")
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation input",
        ) from None

    except Exception:
        logger.exception("Investigation workflow failed")
        raise HTTPException(
            status_code=500,
            detail="Investigation could not be completed",
        ) from None

    if (
        result.get("status") == "completed"
        and isinstance(result.get("structured_report"), dict)
    ):
        try:
            service = InvestigationReportService(db)

            service.save(
                investigation_id=result["investigation_id"],
                user_id=user.id,
                structured_report=result["structured_report"],
            )

        except Exception:
            logger.exception(
                "Failed to persist investigation report %s",
                result.get("investigation_id"),
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Investigation completed, but report "
                    "persistence failed"
                ),
            ) from None

    logger.info(
        "Investigation finished: id=%s status=%s",
        result.get("investigation_id"),
        result.get("status"),
    )

    return result


@router.get("/reports")
def list_investigation_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = InvestigationReportService(db)

        return service.list_reports(
            user_id=user.id,
            limit=limit,
            offset=offset,
        )

    except Exception:
        logger.exception("Failed to list investigation reports")

        raise HTTPException(
            status_code=500,
            detail="Unable to list investigation reports",
        ) from None


@router.get("/{investigation_id}/report")
def get_investigation_report(
    investigation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    canonical_id = validate_investigation_id(
        investigation_id
    )

    try:
        service = InvestigationReportService(db)

        report = service.get(
            investigation_id=canonical_id,
            user_id=user.id,
        )

    except Exception:
        logger.exception("Failed to retrieve investigation report")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve investigation report",
        ) from None

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation report not found",
        )

    return report


@router.get("/{investigation_id}")
def get_investigation_history(
    investigation_id: str,
    user: User = Depends(get_current_user),
):
    canonical_id = validate_investigation_id(
        investigation_id
    )

    try:
        history = AuditService().get_history(
            investigation_id=canonical_id,
            user_id=user.id,
        )

    except Exception:
        logger.exception("Failed to retrieve investigation history")

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
