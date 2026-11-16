
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SeverityLevel = Literal["low", "medium", "high", "critical"]


class InvestigationPreferences(BaseModel):
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


class MandatorySecurityPolicy(BaseModel):
    audit_logging_enabled: Literal[True] = True
    prompt_injection_protection_enabled: Literal[True] = True
    authentication_required: Literal[True] = True
    owner_scoped_data_access: Literal[True] = True


class ConfigurationResponse(BaseModel):
    preferences: InvestigationPreferences
    security_policy: MandatorySecurityPolicy


def effective_configuration(
    preferences: InvestigationPreferences,
) -> ConfigurationResponse:
    return ConfigurationResponse(
        preferences=preferences,
        security_policy=MandatorySecurityPolicy(),
    )
