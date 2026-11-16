
import asyncio
from typing import Any

from apps.api.agents.audited_workflow import (
    AuditedInvestigationWorkflow,
)
from apps.api.agents.evidence_synthesis import (
    synthesize_evidence,
)
from apps.api.agents.investigation_report import (
    build_investigation_report,
)


class SecureInvestigationWorkflow:
    """
    Audited security investigation with:
    - Deterministic security analysis
    - Owner-scoped RAG retrieval
    - Evidence-grounded LLM synthesis
    - Structured investigation reporting

    The audit remains open until all processing
    completes or fails.
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
        """
        Execute an authorized security investigation.

        Workflow:
        1. Execute audited security tools.
        2. Retrieve owner-scoped RAG evidence.
        3. Synthesize current incident findings.
        4. Generate a structured investigation report.
        5. Finalize the investigation audit.
        """

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
                "structured_report": None,
            }

        investigation_id = result["investigation_id"]
        audit = self.audited_workflow.audit

        # Primary evidence: deterministic findings
        # from the submitted security events.
        incident_report = result["report"]

        # Supplementary evidence: authenticated,
        # owner-scoped RAG retrieval results.
        evidence = result.get("evidence", {})
        sources = evidence.get("sources", [])

        try:
            # STEP 1:
            # Generate evidence-grounded AI synthesis.
            #
            # Run the synchronous OpenAI call in a
            # worker thread to avoid blocking the
            # FastAPI event loop.
            synthesis = await asyncio.to_thread(
                synthesize_evidence,
                client=self.client,
                model=self.model,
                request=request,
                sources=sources,
                incident_report=incident_report,
            )

            # STEP 2:
            # Build a deterministic structured report.
            #
            # This operation does not call the LLM
            # or execute any additional tools.
            structured_report = (
                build_investigation_report(
                    investigation_id=investigation_id,
                    report=incident_report,
                    evidence=evidence,
                    synthesis=synthesis,
                )
            )

        except Exception:
            # Record a safe failure event.
            # Do not expose raw logs, documents,
            # model responses, or internal errors.
            audit.record_event(
                investigation_id=investigation_id,
                event_type="evidence_synthesis",
                status="failed",
                details={
                    "error_code": (
                        "INVESTIGATION_PROCESSING_FAILED"
                    ),
                },
            )

            # Mark the investigation as failed.
            audit.finish_investigation(
                investigation_id=investigation_id,
                status="failed",
                error_code=(
                    "INVESTIGATION_PROCESSING_FAILED"
                ),
            )

            return {
                **result,
                "status": "failed",
                "evidence_synthesis": None,
                "synthesis_status": "failed",
                "structured_report": None,
            }

        # STEP 3:
        # Record successful evidence synthesis.
        #
        # This event type is already supported
        # by the existing audit service.
        audit.record_event(
            investigation_id=investigation_id,
            event_type="evidence_synthesis",
            status="completed",
            details={},
        )

        # STEP 4:
        # Finalize the investigation.
        #
        # Do not record a separate "structured_report"
        # audit event because that event type is not
        # currently supported by AuditService.
        audit.finish_investigation(
            investigation_id=investigation_id,
            status="completed",
            severity=incident_report["severity"],
        )

        # STEP 5:
        # Return the completed investigation,
        # including its dashboard-ready report.
        return {
            **result,
            "evidence_synthesis": synthesis,
            "synthesis_status": "completed",
            "structured_report": structured_report,
        }
