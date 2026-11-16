
from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User

from apps.api.agents.report_export_service import (
    ReportExportService,
)


router = APIRouter(
    prefix="/investigations",
    tags=["Report Exports"],
)


def get_export_service(
    db: Session = Depends(get_db),
) -> ReportExportService:
    """
    Create a report export service using the
    request-scoped database session.
    """
    return ReportExportService(db)


def generate_export(
    *,
    investigation_id: str,
    export_format: str,
    user: User,
    service: ReportExportService,
) -> StreamingResponse:
    """
    Validate authorization, generate the requested
    report format, and return a downloadable response.
    """
    try:
        result = service.export(
            investigation_id=investigation_id,
            user_id=user.id,
            export_format=export_format,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation report not found",
        ) from exc

    content = result["content"]
    filename = result["filename"]
    media_type = result["media_type"]

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ============================================================
# Export PDF
# ============================================================

@router.get(
    "/{investigation_id}/export/pdf",
    summary="Download approved investigation report as PDF",
)
def export_investigation_pdf(
    investigation_id: str,
    user: User = Depends(get_current_user),
    service: ReportExportService = Depends(
        get_export_service
    ),
):
    """
    Download a professionally formatted PDF.

    Pending and rejected reports cannot be exported
    when human review is required.
    """
    return generate_export(
        investigation_id=investigation_id,
        export_format="pdf",
        user=user,
        service=service,
    )


# ============================================================
# Export JSON
# ============================================================

@router.get(
    "/{investigation_id}/export/json",
    summary="Download approved investigation report as JSON",
)
def export_investigation_json(
    investigation_id: str,
    user: User = Depends(get_current_user),
    service: ReportExportService = Depends(
        get_export_service
    ),
):
    """
    Download the structured investigation report
    as JSON after server-side authorization.
    """
    return generate_export(
        investigation_id=investigation_id,
        export_format="json",
        user=user,
        service=service,
    )
