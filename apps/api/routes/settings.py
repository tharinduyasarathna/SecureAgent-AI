
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.app.settings_models import UserSettings


router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)


SeverityLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class SettingsPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_security_agent: bool = True
    enable_rag_agent: bool = True
    enable_report_agent: bool = True
    require_human_review: bool = True
    default_severity_threshold: SeverityLevel = "medium"
    max_investigation_events: int = Field(
        default=100,
        ge=1,
        le=10000,
    )
    auto_generate_report: bool = True


class SecurityPolicy(BaseModel):
    audit_logging_enabled: Literal[True] = True
    prompt_injection_protection_enabled: Literal[True] = True
    authentication_required: Literal[True] = True
    owner_scoped_data_access: Literal[True] = True


class SettingsResponse(BaseModel):
    preferences: SettingsPreferences
    security_policy: SecurityPolicy


def build_response(
    settings: UserSettings | None,
) -> SettingsResponse:
    if settings is None:
        preferences = SettingsPreferences()
    else:
        preferences = SettingsPreferences.model_validate(
            {
                key: getattr(settings, key)
                for key in SettingsPreferences.model_fields
            }
        )

    return SettingsResponse(
        preferences=preferences,
        security_policy=SecurityPolicy(),
    )


@router.get(
    "",
    response_model=SettingsResponse,
)
def get_user_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = db.get(UserSettings, user.id)
    return build_response(settings)


@router.put(
    "",
    response_model=SettingsResponse,
)
def update_user_settings(
    preferences: SettingsPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = db.get(UserSettings, user.id)

    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    for key, value in preferences.model_dump().items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return build_response(settings)
