import asyncio
from typing import Any

from apps.api.agents.audited_workflow import AuditedInvestigationWorkflow
from apps.api.agents.security_analysis_agent import SecurityAnalysisAgent
from apps.api.agents.rag_knowledge_agent import RAGKnowledgeAgent
from apps.api.agents.report_generation_agent import ReportGenerationAgent
from apps.api.agents.delegation_policy import DelegationContext, DelegationPolicy
from apps.api.agents.investigation_preferences import InvestigationPreferences


class SpecialistInvestigationWorkflow:
    def __init__(self, *, security_agent: SecurityAnalysisAgent,
                 rag_agent: RAGKnowledgeAgent, delegation_policy: DelegationPolicy):
        self.security_agent = security_agent
        self.rag_agent = rag_agent
        self.delegation_policy = delegation_policy

    async def run(
        self, *, db, user_id: int, request: str, events: list[dict],
        granted_permissions: set[str], top_k: int = 5,
        document_id: int | None = None, investigation_id: str | None = None,
        preferences: InvestigationPreferences | None = None,
    ) -> dict:
        preferences = preferences or InvestigationPreferences()
        if type(user_id) is not int or user_id <= 0:
            raise ValueError('Invalid authenticated user')
        if not isinstance(granted_permissions, set) or 'security:read' not in granted_permissions:
            raise PermissionError('Missing security:read permission')
        if not isinstance(investigation_id, str) or not investigation_id:
            raise ValueError('Invalid investigation ID')
        if type(top_k) is not int or not 1 <= top_k <= 5:
            raise ValueError('Invalid top_k')
        if document_id is not None and (type(document_id) is not int or document_id <= 0):
            raise ValueError('Invalid document_id')
        if not preferences.enable_security_agent:
            raise ValueError('Security analysis is required for investigations')

        context = DelegationContext(
            user_id=user_id, investigation_id=investigation_id,
            granted_permissions=set(granted_permissions),
        )
        self.delegation_policy.record_execution(agent_name='security_analysis', context=context)
        investigation = await asyncio.to_thread(
            self.security_agent.run, request=request, events=events,
            granted_permissions=granted_permissions, investigation_id=investigation_id,
        )
        if investigation.get('investigation_id') != investigation_id:
            raise RuntimeError('INVESTIGATION_ID_MISMATCH')
        if investigation.get('status') != 'completed':
            return {**investigation, 'evidence': {'results_count': 0, 'sources': []}}

        evidence = {'results_count': 0, 'sources': []}
        if preferences.enable_rag_agent:
            self.delegation_policy.record_execution(agent_name='rag_knowledge', context=context)
            evidence = await self.rag_agent.run(
                db=db, user_id=user_id, query=request,
                granted_permissions=granted_permissions, top_k=top_k,
                document_id=document_id,
            )

        report = dict(investigation['report'])
        report['evidence_references'] = [
            {
                'source': source['source'], 'document_id': source['document_id'],
                'chunk_id': source['chunk_id'], 'filename': source['filename'],
                'similarity': source['similarity'],
            }
            for source in evidence['sources']
        ]
        report['evidence_status'] = (
            'disabled' if not preferences.enable_rag_agent
            else 'retrieved' if evidence['results_count'] > 0
            else 'no_documents_found'
        )
        return {
            **investigation, 'report': report, 'evidence': evidence,
            '_delegation_context': context,
        }


class SupervisorAgent:
    REQUIRED_PERMISSION = 'security:read'

    def __init__(self, *, client: Any, model: str, audit_service=None):
        if client is None:
            raise ValueError('An AI client is required')
        if not isinstance(model, str) or not model.strip():
            raise ValueError('A valid model is required')
        self.client = client
        self.model = model
        self.delegation_policy = DelegationPolicy()
        self.security_agent = SecurityAnalysisAgent(client=client, model=model)
        self.rag_agent = RAGKnowledgeAgent()
        self.report_agent = ReportGenerationAgent(client=client, model=model)
        self.audited_workflow = AuditedInvestigationWorkflow(
            client=client, model=model, audit_service=audit_service,
        )
        self.audited_workflow.workflow = SpecialistInvestigationWorkflow(
            security_agent=self.security_agent, rag_agent=self.rag_agent,
            delegation_policy=self.delegation_policy,
        )

    def _finalize_failed(self, *, investigation_id: str, error_code: str) -> None:
        audit = self.audited_workflow.audit
        try:
            audit.record_event(
                investigation_id=investigation_id, event_type='evidence_synthesis',
                status='failed', details={'error_code': error_code},
            )
        finally:
            audit.finish_investigation(
                investigation_id=investigation_id, status='failed', error_code=error_code,
            )

    def _finalize_completed(self, *, investigation_id: str, severity: str) -> None:
        audit = self.audited_workflow.audit
        audit.record_event(
            investigation_id=investigation_id, event_type='evidence_synthesis',
            status='completed', details={},
        )
        audit.finish_investigation(
            investigation_id=investigation_id, status='completed', severity=severity,
        )

    async def run(
        self, *, db, user_id: int, request: str, events: list[dict],
        granted_permissions: set[str], top_k: int = 5,
        document_id: int | None = None,
        preferences: InvestigationPreferences | None = None,
    ) -> dict:
        preferences = preferences or InvestigationPreferences()
        if type(user_id) is not int or user_id <= 0:
            raise ValueError('Invalid authenticated user')
        if not isinstance(granted_permissions, set) or self.REQUIRED_PERMISSION not in granted_permissions:
            raise PermissionError('Missing security:read permission')
        if not isinstance(request, str) or not 1 <= len(request.strip()) <= 2000:
            raise ValueError('Request must contain 1-2000 characters')
        if not isinstance(events, list) or len(events) > 1000:
            raise ValueError('Invalid security events')
        if len(events) > preferences.max_investigation_events:
            raise ValueError('Investigation exceeds configured event limit')
        if type(top_k) is not int or not 1 <= top_k <= 5:
            raise ValueError('Invalid top_k')
        if document_id is not None and (type(document_id) is not int or document_id <= 0):
            raise ValueError('Invalid document_id')
        if not preferences.enable_security_agent:
            raise ValueError('Security analysis must remain enabled to run investigations')

        result = await self.audited_workflow.run(
            db=db, user_id=user_id, request=request, events=events,
            granted_permissions=granted_permissions, top_k=top_k,
            document_id=document_id, finalize=False, preferences=preferences,
        )
        context = result.pop('_delegation_context', None)
        if result.get('status') != 'completed':
            return {
                **result, 'evidence_synthesis': None,
                'synthesis_status': 'skipped', 'structured_report': None,
            }

        investigation_id = result['investigation_id']
        try:
            if not isinstance(context, DelegationContext):
                raise RuntimeError('Missing delegation context')
            if context.investigation_id != investigation_id:
                raise RuntimeError('INVESTIGATION_ID_MISMATCH')
            if context.user_id != user_id:
                raise RuntimeError('Delegation user mismatch')

            expected = {'security_analysis': 1}
            if preferences.enable_rag_agent:
                expected['rag_knowledge'] = 1
            if context.execution_counts != expected:
                raise RuntimeError('Invalid delegation sequence')

            report_result = {
                'structured_report': None,
                'evidence_synthesis': None,
                'synthesis_status': 'skipped',
            }
            if preferences.enable_report_agent and preferences.auto_generate_report:
                self.delegation_policy.record_execution(
                    agent_name='report_generation', context=context,
                )
                report_result = await self.report_agent.run(
                    investigation_id=investigation_id, request=request,
                    incident_report=result['report'], evidence=result.get('evidence', {}),
                    granted_permissions=granted_permissions,
                )

            report_result['review_required'] = preferences.require_human_review
            report_result['review_status'] = (
                'pending' if preferences.require_human_review else 'not_required'
            )
            report_result['severity_threshold'] = preferences.default_severity_threshold
        except asyncio.CancelledError:
            self._finalize_failed(
                investigation_id=investigation_id, error_code='INVESTIGATION_CANCELLED',
            )
            raise
        except Exception:
            self._finalize_failed(
                investigation_id=investigation_id,
                error_code='INVESTIGATION_PROCESSING_FAILED',
            )
            raise

        self._finalize_completed(
            investigation_id=investigation_id, severity=result['report']['severity'],
        )
        return {**result, **report_result}
