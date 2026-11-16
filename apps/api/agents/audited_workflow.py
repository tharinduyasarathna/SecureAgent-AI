from uuid import uuid4

from apps.api.agents.audit_service import AuditService
from apps.api.agents.evidence_workflow import EvidenceInvestigationWorkflow
from apps.api.agents.investigation_preferences import InvestigationPreferences


class AuditedInvestigationWorkflow:
    def __init__(self, *, client, model: str, audit_service: AuditService | None = None):
        self.workflow = EvidenceInvestigationWorkflow(client=client, model=model)
        self.audit = audit_service if audit_service is not None else AuditService()

    async def run(
        self, *, db, user_id: int, request: str, events: list[dict],
        granted_permissions: set[str], top_k: int = 5,
        document_id: int | None = None, finalize: bool = True,
        preferences: InvestigationPreferences | None = None,
    ) -> dict:
        if type(finalize) is not bool:
            raise ValueError('finalize must be a boolean')

        preferences = preferences or InvestigationPreferences()
        investigation_id = str(uuid4())
        self.audit.start_investigation(investigation_id=investigation_id, user_id=user_id)

        try:
            if not isinstance(granted_permissions, set) or 'security:read' not in granted_permissions:
                self.audit.finish_investigation(
                    investigation_id=investigation_id,
                    status='denied', error_code='PERMISSION_DENIED',
                )
                raise PermissionError('Missing security:read permission')

            result = await self.workflow.run(
                db=db, user_id=user_id, request=request, events=events,
                granted_permissions=granted_permissions, top_k=top_k,
                document_id=document_id, investigation_id=investigation_id,
                preferences=preferences,
            )
            if result.get('investigation_id') != investigation_id:
                raise RuntimeError('INVESTIGATION_ID_MISMATCH')

            for step in result.get('steps', []):
                self.audit.record_event(
                    investigation_id=investigation_id, event_type='tool_executed',
                    status='completed', tool_name=step['tool_name'],
                    details={'step': step['step']},
                )

            evidence = result.get('evidence') or {}
            sources = evidence.get('sources', [])
            self.audit.record_event(
                investigation_id=investigation_id, event_type='evidence_retrieved',
                status='completed', details={'source_count': len(sources)},
            )
            for source in sources:
                self.audit.record_event(
                    investigation_id=investigation_id, event_type='evidence_retrieved',
                    status='completed', details={
                        'document_id': source['document_id'], 'chunk_id': source['chunk_id'],
                    },
                )

            if result['status'] == 'completed':
                if finalize:
                    self.audit.finish_investigation(
                        investigation_id=investigation_id, status='completed',
                        severity=result['report']['severity'],
                    )
            else:
                self.audit.finish_investigation(
                    investigation_id=investigation_id, status='failed',
                    error_code='WORKFLOW_NOT_COMPLETED',
                )
            return result

        except PermissionError:
            raise
        except BaseException:
            history = self.audit.get_history(
                investigation_id=investigation_id, user_id=user_id,
            )
            if history is not None and history['status'] == 'started':
                self.audit.finish_investigation(
                    investigation_id=investigation_id, status='failed',
                    error_code='INVESTIGATION_FAILED',
                )
            raise
