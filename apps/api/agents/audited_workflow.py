
from uuid import uuid4

from apps.api.agents.audit_service import AuditService
from apps.api.agents.evidence_workflow import (
    EvidenceInvestigationWorkflow,
)


class AuditedInvestigationWorkflow:
    """
    Persist investigation lifecycle and evidence metadata.

    The caller must supply an authenticated user ID
    and server-derived permissions.

    By default, investigations are finalized immediately.

    When finalize=False, a successfully completed
    investigation remains open so that a trusted
    orchestration layer can perform and audit
    additional operations such as evidence synthesis.
    """

    def __init__(
        self,
        *,
        client,
        model: str,
        audit_service: AuditService | None = None,
    ):
        self.workflow = EvidenceInvestigationWorkflow(
            client=client,
            model=model,
        )

        self.audit = (
            audit_service
            if audit_service is not None
            else AuditService()
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
        finalize: bool = True,
    ) -> dict:

        # Validate the finalization flag.
        if type(finalize) is not bool:
            raise ValueError(
                "finalize must be a boolean"
            )

        # This UUID is authoritative for the
        # entire investigation lifecycle.
        investigation_id = str(uuid4())

        # Fail closed if the initial audit record
        # cannot be persisted.
        self.audit.start_investigation(
            investigation_id=investigation_id,
            user_id=user_id,
        )

        try:
            # Record authorization denial before
            # invoking the LLM or any security tools.
            if (
                not isinstance(granted_permissions, set)
                or "security:read"
                not in granted_permissions
            ):
                self.audit.finish_investigation(
                    investigation_id=investigation_id,
                    status="denied",
                    error_code="PERMISSION_DENIED",
                )

                raise PermissionError(
                    "Missing security:read permission"
                )

            # Propagate the authoritative investigation
            # ID into the evidence and agent workflows.
            result = await self.workflow.run(
                db=db,
                user_id=user_id,
                request=request,
                events=events,
                granted_permissions=granted_permissions,
                top_k=top_k,
                document_id=document_id,
                investigation_id=investigation_id,
            )

            # Never silently overwrite an ID returned
            # by the downstream investigation workflow.
            if (
                result.get("investigation_id")
                != investigation_id
            ):
                raise RuntimeError(
                    "INVESTIGATION_ID_MISMATCH"
                )

            # Record execution of approved security tools.
            for step in result.get("steps", []):
                self.audit.record_event(
                    investigation_id=investigation_id,
                    event_type="tool_executed",
                    status="completed",
                    tool_name=step["tool_name"],
                    details={
                        "step": step["step"],
                    },
                )

            # Record evidence retrieval metadata only.
            # Never store raw document contents.
            evidence = result.get("evidence", {})
            sources = evidence.get("sources", [])

            self.audit.record_event(
                investigation_id=investigation_id,
                event_type="evidence_retrieved",
                status="completed",
                details={
                    "source_count": len(sources),
                },
            )

            for source in sources:
                self.audit.record_event(
                    investigation_id=investigation_id,
                    event_type="evidence_retrieved",
                    status="completed",
                    details={
                        "document_id": source["document_id"],
                        "chunk_id": source["chunk_id"],
                    },
                )

            if result["status"] == "completed":
                # Direct callers retain the original
                # immediate-finalization behavior.
                if finalize:
                    self.audit.finish_investigation(
                        investigation_id=investigation_id,
                        status="completed",
                        severity=result["report"][
                            "severity"
                        ],
                    )

                # With finalize=False, the audit remains
                # in "started" state. The trusted caller
                # must finalize it after synthesis.

            else:
                # Incomplete investigations are always
                # finalized as failed, even when the
                # caller requests deferred finalization.
                self.audit.finish_investigation(
                    investigation_id=investigation_id,
                    status="failed",
                    error_code="WORKFLOW_NOT_COMPLETED",
                )

            return result

        except PermissionError:
            # Authorization denial was already
            # finalized above.
            raise

        except Exception:
            # Attempt to finalize an investigation
            # that failed while its audit was open.
            #
            # Audit failures must never be silently
            # ignored or converted into success.
            history = self.audit.get_history(
                investigation_id=investigation_id,
                user_id=user_id,
            )

            if (
                history is not None
                and history["status"] == "started"
            ):
                self.audit.finish_investigation(
                    investigation_id=investigation_id,
                    status="failed",
                    error_code="INVESTIGATION_FAILED",
                )

            raise
