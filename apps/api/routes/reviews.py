
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User

from apps.api.agents.investigation_review_service import (
    InvestigationReviewService,
    ReviewConflictError,
    ReviewNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations",
    tags=["Investigation Reviews"],
)


class ReviewDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    notes: str = Field(min_length=1, max_length=2000)


@router.get("/{investigation_id}/review")
def get_review(
    investigation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = InvestigationReviewService(db)

    try:
        review = service.get(
            investigation_id=investigation_id,
            user_id=user.id,
        )

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation ID",
        ) from None

    except Exception:
        logger.exception("Unable to retrieve review")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve review",
        ) from None

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    return review


@router.post("/{investigation_id}/review")
def submit_review(
    investigation_id: str,
    payload: ReviewDecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = InvestigationReviewService(db)

    try:
        return service.decide(
            investigation_id=investigation_id,
            user_id=user.id,
            decision=payload.decision,
            notes=payload.notes,
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        ) from None

    except ReviewConflictError:
        raise HTTPException(
            status_code=409,
            detail="Review is not pending",
        ) from None

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None

    except Exception:
        logger.exception("Investigation review failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to submit review",
        ) from None


@router.get("/{investigation_id}/review/history")
def get_review_history(
    investigation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = InvestigationReviewService(db)

    try:
        return {
            "items": service.history(
                investigation_id=investigation_id,
                user_id=user.id,
            )
        }

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        ) from None

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid investigation ID",
        ) from None

    except Exception:
        logger.exception("Unable to retrieve review history")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve review history",
        ) from None
