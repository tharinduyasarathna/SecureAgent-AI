
from collections import Counter
from datetime import datetime, timezone
from typing import Any


ALLOWED_EVENT_TYPES = {
    "login_success",
    "login_failure",
    "malware_detected",
    "network_connection",
}


def analyze_security_logs(
    *,
    events: list[dict[str, Any]],
) -> dict:
    """
    Analyze synthetic security events without modifying them.

    This is a deterministic, read-only analysis tool.
    """

    if not isinstance(events, list):
        raise ValueError("Events must be a list")

    if len(events) > 1000:
        raise ValueError("Maximum 1000 events allowed")

    event_counts = Counter()
    failed_logins_by_ip = Counter()
    findings = []

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(
                f"Event {index} must be an object"
            )

        event_type = event.get("event_type")
        source_ip = event.get("source_ip")

        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(
                f"Invalid event type at index {index}"
            )

        if not isinstance(source_ip, str) or not source_ip:
            raise ValueError(
                f"Invalid source IP at index {index}"
            )

        try:
            timestamp = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ValueError(
                f"Invalid timestamp at index {index}"
            )

        if timestamp.tzinfo is None:
            raise ValueError(
                f"Timestamp must include timezone at index {index}"
            )

        event_counts[event_type] += 1

        if event_type == "login_failure":
            failed_logins_by_ip[source_ip] += 1

    for source_ip, count in failed_logins_by_ip.items():
        if count >= 5:
            findings.append({
                "type": "repeated_login_failures",
                "source_ip": source_ip,
                "count": count,
                "severity": "medium",
                "description": (
                    f"{count} failed logins detected "
                    f"from {source_ip}"
                ),
            })

    if event_counts["malware_detected"] > 0:
        findings.append({
            "type": "malware_detection",
            "count": event_counts["malware_detected"],
            "severity": "high",
            "description": "Malware detection events observed",
        })

    return {
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "findings": findings,
        "finding_count": len(findings),
        "analyzed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }
