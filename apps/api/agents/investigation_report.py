
from datetime import datetime, timezone
from typing import Any


SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

ACTION_PRIORITY = {
    "critical": "P1",
    "high": "P1",
    "medium": "P2",
    "low": "P3",
}

DEFAULT_ACTIONS = {
    "successful_login_after_failures": [
        "Verify whether the successful login was authorized",
        "Review account activity after the successful login",
        "Investigate the source IP and affected account",
        "Revoke suspicious sessions if compromise is suspected",
        "Reset affected credentials if warranted",
        "Enforce MFA and SSH access controls",
    ],
    "repeated_login_failures": [
        "Investigate the source IP and targeted accounts",
        "Review authentication logs for additional attempts",
        "Apply appropriate rate limiting and access controls",
    ],
    "malware_detection": [
        "Review the malware detection and supporting telemetry",
        "Investigate affected systems and processes",
        "Contain affected systems if malicious activity is confirmed",
    ],
}


def _severity(value: Any) -> str:
    if value not in SEVERITY_RANK:
        return "low"
    return value


def _unique_event_indices(
    values: Any,
    total_events: int,
) -> list[int]:
    if not isinstance(values, list):
        return []

    return sorted({
        value
        for value in values
        if (
            type(value) is int
            and 0 <= value < total_events
        )
    })


def _build_findings(
    findings: list[dict],
    total_events: int,
) -> list[dict]:
    structured = []

    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ValueError("Invalid security finding")

        severity = _severity(
            finding.get("severity")
        )

        finding_type = str(
            finding.get("type", "unknown")
        )

        event_indices = _unique_event_indices(
            finding.get("evidence_event_indices", []),
            total_events,
        )

        actions = finding.get("recommended_actions")

        if not isinstance(actions, list):
            actions = DEFAULT_ACTIONS.get(
                finding_type, []
            )

        actions = [
            action
            for action in actions
            if isinstance(action, str) and action.strip()
        ][:10]

        structured.append({
            "finding_id": f"F-{index:03d}",
            "type": finding_type,
            "severity": severity,
            "title": finding_type.replace(
                "_", " "
            ).title(),
            "description": str(
                finding.get("description", "")
            ),
            "source_ip": finding.get("source_ip"),
            "username": finding.get("username"),
            "evidence_event_indices": event_indices,
            "evidence_references": [
                f"event:{event_index}"
                for event_index in event_indices
            ],
            "recommended_actions": actions,
        })

    structured.sort(
        key=lambda finding: (
            -SEVERITY_RANK[finding["severity"]],
            finding["finding_id"],
        )
    )

    return structured


def _build_recommendations(
    findings: list[dict],
) -> list[dict]:
    recommendations = []
    seen = {}

    for finding in findings:
        priority = ACTION_PRIORITY[
            finding["severity"]
        ]

        for action in finding["recommended_actions"]:
            normalized = " ".join(
                action.lower().split()
            )

            if normalized in seen:
                existing = recommendations[
                    seen[normalized]
                ]

                if priority < existing["priority"]:
                    existing["priority"] = priority

                if (
                    finding["finding_id"]
                    not in existing["finding_ids"]
                ):
                    existing["finding_ids"].append(
                        finding["finding_id"]
                    )

                continue

            seen[normalized] = len(recommendations)

            recommendations.append({
                "priority": priority,
                "action": action,
                "finding_ids": [
                    finding["finding_id"]
                ],
                "status": "recommended",
            })

    recommendations.sort(
        key=lambda item: (
            item["priority"],
            item["action"].lower(),
        )
    )

    for index, item in enumerate(
        recommendations, start=1
    ):
        item["action_id"] = f"A-{index:03d}"

    return recommendations


def build_investigation_report(
    *,
    investigation_id: str,
    report: dict,
    evidence: dict | None,
    synthesis: dict | None,
) -> dict:
    """
    Create a dashboard-ready investigation report.

    No LLM calls, database writes, network requests,
    or security tool execution occur here.

    The deterministic incident report determines
    severity. Synthesis provides explanatory context.
    """

    if not isinstance(
        investigation_id, str
    ) or not investigation_id.strip():
        raise ValueError("Invalid investigation ID")

    if not isinstance(report, dict):
        raise ValueError("Invalid incident report")

    if synthesis is not None and not isinstance(
        synthesis, dict
    ):
        raise ValueError("Invalid synthesis")

    if evidence is not None and not isinstance(
        evidence, dict
    ):
        raise ValueError("Invalid evidence")

    severity = report.get("severity")

    if severity not in SEVERITY_RANK:
        raise ValueError("Invalid incident severity")

    raw_findings = report.get("findings", [])

    if not isinstance(raw_findings, list):
        raise ValueError("Invalid findings")

    statistics = report.get(
        "authentication_statistics", {}
    )

    if not isinstance(statistics, dict):
        raise ValueError("Invalid statistics")

    total_events = statistics.get("total_events")

    if type(total_events) is not int:
        total_events = sum(
            count
            for count in report.get(
                "event_counts", {}
            ).values()
            if type(count) is int and count >= 0
        )

    findings = _build_findings(
        raw_findings,
        total_events,
    )

    recommendations = _build_recommendations(
        findings
    )

    sources = (
        evidence.get("sources", [])
        if evidence else []
    )

    if not isinstance(sources, list):
        raise ValueError("Invalid evidence sources")

    source_ids = (
        synthesis.get("source_ids", [])
        if synthesis else []
    )

    supplementary_sources = []

    for source in sources:
        if not isinstance(source, dict):
            continue

        chunk_id = source.get("chunk_id")

        supplementary_sources.append({
            "document_id": source.get(
                "document_id"
            ),
            "chunk_id": chunk_id,
            "filename": source.get("filename"),
            "similarity": source.get(
                "similarity"
            ),
            "cited_in_synthesis": (
                chunk_id in source_ids
            ),
            "role": "supplementary_context",
        })

    executive_summary = (
        synthesis.get("summary", "")
        if synthesis else ""
    )

    if not executive_summary:
        executive_summary = report.get(
            "summary", ""
        )

    limitations = (
        synthesis.get("limitations", "")
        if synthesis else ""
    )

    return {
        "report_version": "1.0",
        "investigation_id": investigation_id,
        "title": "Security Investigation Report",
        "status": "completed",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "executive_summary": executive_summary,
        "risk_assessment": {
            "severity": severity,
            "risk_indicator": statistics.get(
                "risk_indicator",
                "unknown",
            ),
            "ai_risk_level": (
                synthesis.get("risk_level")
                if synthesis else None
            ),
            "compromise_confirmed": False,
            "compromise_status": "not_established",
        },
        "overview": {
            "total_events": total_events,
            "total_findings": len(findings),
            "high_severity_findings": sum(
                1
                for finding in findings
                if finding["severity"] in {
                    "high", "critical"
                }
            ),
            "event_counts": report.get(
                "event_counts", {}
            ),
            "authentication_statistics": statistics,
        },
        "findings": findings,
        "recommendations": recommendations,
        "evidence": {
            "primary_source": (
                "supplied_security_events"
            ),
            "event_reference_format": (
                "zero_based_event_index"
            ),
            "supplementary_sources": (
                supplementary_sources
            ),
            "supplementary_sources_count": len(
                supplementary_sources
            ),
            "synthesis_cited_source_ids": (
                source_ids
            ),
        },
        "limitations": limitations,
        "review_status": "pending_analyst_review",
    }
