
import asyncio
from typing import Any

from apps.api.agents.evidence_synthesis import synthesize_evidence
from apps.api.agents.investigation_report import build_investigation_report


class ReportGenerationAgent:
    VALID_SEVERITIES = {"low", "medium", "high", "critical"}
    VALID_RISK_LEVELS = {"low", "medium", "high", "unknown"}

    def __init__(self, *, client: Any, model: str):
        if client is None:
            raise ValueError("An AI client is required")

        if not isinstance(model, str) or not model.strip():
            raise ValueError("A valid model is required")

        self.client = client
        self.model = model

    async def run(
        self,
        *,
        investigation_id: str,
        request: str,
        incident_report: dict,
        evidence: dict,
        granted_permissions: set[str],
    ) -> dict:
        if (
            not isinstance(granted_permissions, set)
            or "security:read" not in granted_permissions
        ):
            raise PermissionError("Missing security:read permission")

        if not isinstance(investigation_id, str) or not investigation_id.strip():
            raise ValueError("Invalid investigation ID")

        if not isinstance(request, str) or not 1 <= len(request.strip()) <= 2000:
            raise ValueError("Invalid investigation request")

        if not isinstance(incident_report, dict):
            raise ValueError("Invalid incident report")

        if incident_report.get("severity") not in self.VALID_SEVERITIES:
            raise ValueError("Invalid incident severity")

        if not isinstance(incident_report.get("findings"), list):
            raise ValueError("Invalid security findings")

        if not isinstance(incident_report.get("event_counts"), dict):
            raise ValueError("Invalid event counts")

        if not isinstance(evidence, dict):
            raise ValueError("Invalid supporting evidence")

        sources = evidence.get("sources", [])

        if not isinstance(sources, list):
            raise ValueError("Invalid evidence sources")

        synthesis = await asyncio.to_thread(
            synthesize_evidence,
            client=self.client,
            model=self.model,
            request=request,
            sources=sources,
            incident_report=incident_report,
        )

        self._validate_synthesis(synthesis)

        structured_report = build_investigation_report(
            investigation_id=investigation_id,
            report=incident_report,
            evidence=evidence,
            synthesis=synthesis,
        )

        self._validate_report(
            structured_report,
            investigation_id=investigation_id,
            incident_report=incident_report,
        )

        return {
            "evidence_synthesis": synthesis,
            "synthesis_status": "completed",
            "structured_report": structured_report,
        }

    def _validate_synthesis(self, synthesis: dict) -> None:
        if not isinstance(synthesis, dict):
            raise RuntimeError("Invalid evidence synthesis")

        if not isinstance(synthesis.get("summary"), str):
            raise RuntimeError("Missing executive summary")

        if not synthesis["summary"].strip():
            raise RuntimeError("Empty executive summary")

        if synthesis.get("risk_level") not in self.VALID_RISK_LEVELS:
            raise RuntimeError("Invalid synthesized risk level")

        if not isinstance(synthesis.get("source_ids"), list):
            raise RuntimeError("Invalid synthesis citations")

        if not isinstance(synthesis.get("limitations"), str):
            raise RuntimeError("Invalid investigation limitations")

    def _validate_report(
        self,
        report: dict,
        *,
        investigation_id: str,
        incident_report: dict,
    ) -> None:
        if not isinstance(report, dict):
            raise RuntimeError("Invalid structured report")

        if report.get("investigation_id") != investigation_id:
            raise RuntimeError("Report investigation ID mismatch")

        if report.get("status") != "completed":
            raise RuntimeError("Report generation incomplete")

        if report.get("review_status") != "pending_analyst_review":
            raise RuntimeError("Invalid analyst review status")

        if not isinstance(report.get("executive_summary"), str):
            raise RuntimeError("Invalid executive summary")

        risk_assessment = report.get("risk_assessment")

        if not isinstance(risk_assessment, dict):
            raise RuntimeError("Missing risk assessment")

        if risk_assessment.get("severity") != incident_report["severity"]:
            raise RuntimeError("Report severity mismatch")

        if risk_assessment.get("compromise_status") != "not_established":
            raise RuntimeError("Unexpected compromise assessment")

        findings = report.get("findings")
        recommendations = report.get("recommendations")
        overview = report.get("overview")
        report_evidence = report.get("evidence")

        if not isinstance(findings, list):
            raise RuntimeError("Invalid report findings")

        if not isinstance(recommendations, list):
            raise RuntimeError("Invalid recommendations")

        if not isinstance(overview, dict):
            raise RuntimeError("Invalid report overview")

        if not isinstance(report_evidence, dict):
            raise RuntimeError("Invalid evidence references")

        if overview.get("total_findings") != len(findings):
            raise RuntimeError("Report finding count mismatch")

        finding_ids = set()

        for finding in findings:
            if not isinstance(finding, dict):
                raise RuntimeError("Invalid report finding")

            finding_id = finding.get("finding_id")

            if not isinstance(finding_id, str) or finding_id in finding_ids:
                raise RuntimeError("Duplicate or invalid finding ID")

            finding_ids.add(finding_id)

            if finding.get("severity") not in self.VALID_SEVERITIES:
                raise RuntimeError("Invalid finding severity")

            if not isinstance(finding.get("evidence_references"), list):
                raise RuntimeError("Missing finding evidence references")

        action_ids = set()

        for recommendation in recommendations:
            if not isinstance(recommendation, dict):
                raise RuntimeError("Invalid recommendation")

            action_id = recommendation.get("action_id")

            if not isinstance(action_id, str) or action_id in action_ids:
                raise RuntimeError("Duplicate or invalid action ID")

            action_ids.add(action_id)

            if recommendation.get("priority") not in {"P1", "P2", "P3"}:
                raise RuntimeError("Invalid remediation priority")

            linked_findings = recommendation.get("finding_ids")

            if not isinstance(linked_findings, list):
                raise RuntimeError("Invalid recommendation references")

            if any(
                finding_id not in finding_ids
                for finding_id in linked_findings
            ):
                raise RuntimeError("Unknown recommendation finding reference")
