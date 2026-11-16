from dataclasses import dataclass
from typing import Literal

Severity = Literal['low', 'medium', 'high', 'critical']


@dataclass(frozen=True)
class InvestigationPreferences:
    enable_security_agent: bool = True
    enable_rag_agent: bool = True
    enable_report_agent: bool = True
    require_human_review: bool = True
    default_severity_threshold: Severity = 'medium'
    max_investigation_events: int = 100
    auto_generate_report: bool = True

    @classmethod
    def from_record(cls, record):
        if record is None:
            return cls()
        return cls(**{
            key: getattr(record, key)
            for key in cls.__dataclass_fields__
        })
