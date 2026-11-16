
import asyncio
from typing import Any

from apps.api.agents.audited_workflow import (
    AuditedInvestigationWorkflow,
)
from apps.api.agents.evidence_synthesis import (
    synthesize_evidence,
)


class SecureInvestigationWorkflow:
    """
    Audited security investigation with tool-free
    LLM evidence synthesis.

    The investigation audit remains open until
    synthesis completes or fails.
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        audit_service=None,
    ):
        self.client = client
        self.model = model

        self.audited_workflow = (
            AuditedInvestigationWorkflow(
                client=client,
                model=model,
                audit_service=audit_service,
            )
        )

    async def run(
        self,
        *,
        db,
        user_id: int,
        request: str,
        events: list[dict],
        granted_permissions: set[str],
        top_k: int = 5,
        document_id: int | None = None,
    ) -> dict:

        result = await self.audited_workflow.run(
            db=db,
            user_id=user_id,
            request=request,
            events=events,
            granted_permissions=granted_permissions,
            top_k=top_k,
            document_id=document_id,
            finalize=False,
        )

        # Incomplete investigations are already
        # finalized by AuditedInvestigationWorkflow.
        if result.get("status") != "completed":
            return {
                **result,
                "evidence_synthesis": None,
                "synthesis_status": "skipped",
            }

        investigation_id = result["investigation_id"]
        audit = self.audited_workflow.audit

        sources = result.get(
            "evidence", {}
        ).get("sources", [])

        try:
            synthesis = await asyncio.to_thread(
                synthesize_evidence,
                client=self.client,
                model=self.model,
                request=request,
                sources=sources,
            )

        except Exception:
            # Record a safe failure event without
            # exposing raw model errors.
            audit.record_event(
                investigation_id=investigation_id,
                event_type="evidence_synthesis",
                status="failed",
                details={
                    "error_code": "SYNTHESIS_FAILED",
                },
            )

            audit.finish_investigation(
                investigation_id=investigation_id,
                status="failed",
                error_code="SYNTHESIS_FAILED",
            )

            # A failed synthesis must not produce
            # a completed investigation response.
            return {
                **result,
                "status": "failed",
                "evidence_synthesis": None,
                "synthesis_status": "failed",
            }

        # Audit the synthesis outcome before
        # finalizing the investigation.
        audit.record_event(
            investigation_id=investigation_id,
            event_type="evidence_synthesis",
            status="completed",
            details={},
        )

        audit.finish_investigation(
            investigation_id=investigation_id,
            status="completed",
            severity=result["report"]["severity"],
        )

        return {
            **result,
            "evidence_synthesis": synthesis,
            "synthesis_status": "completed",
        }
