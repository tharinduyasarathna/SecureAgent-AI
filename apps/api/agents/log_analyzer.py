
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


ALLOWED_EVENT_TYPES = {
    "login_success",
    "login_failure",
    "malware_detected",
    "network_connection",
}

FAILURE_THRESHOLD = 5
CORRELATION_WINDOW = timedelta(minutes=15)


def analyze_security_logs(
    *,
    events: list[dict[str, Any]],
) -> dict:
    """
    Deterministic, read-only security event analysis.

    Detects:
    - Repeated login failures from a source IP
    - Successful login after repeated failures
    - Malware detection events

    Correlation uses a 15-minute lookback window.
    """

    if not isinstance(events, list):
        raise ValueError("Events must be a list")

    if len(events) > 1000:
        raise ValueError("Maximum 1000 events allowed")

    event_counts = Counter()
    failed_logins_by_ip = Counter()
    parsed_events = []
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

        if (
            not isinstance(source_ip, str)
            or not source_ip.strip()
        ):
            raise ValueError(
                f"Invalid source IP at index {index}"
            )

        try:
            timestamp = datetime.fromisoformat(
                event["timestamp"].replace(
                    "Z", "+00:00"
                )
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
        ):
            raise ValueError(
                f"Invalid timestamp at index {index}"
            ) from None

        if timestamp.tzinfo is None:
            raise ValueError(
                f"Timestamp must include timezone "
                f"at index {index}"
            )

        timestamp = timestamp.astimezone(timezone.utc)
        source_ip = source_ip.strip()

        event_counts[event_type] += 1

        parsed_events.append({
            "index": index,
            "timestamp": timestamp,
            "event_type": event_type,
            "source_ip": source_ip,
            "username": event.get("username"),
        })

        if event_type == "login_failure":
            failed_logins_by_ip[source_ip] += 1

    # Preserve the original events and correlate
    # them chronologically.
    ordered_events = sorted(
        parsed_events,
        key=lambda event: (
            event["timestamp"],
            event["index"],
        ),
    )

    failures_by_ip = defaultdict(list)
    correlated_successes = set()

    for event in ordered_events:
        event_type = event["event_type"]
        source_ip = event["source_ip"]
        timestamp = event["timestamp"]

        if event_type == "login_failure":
            failures_by_ip[source_ip].append(event)
            continue

        if event_type != "login_success":
            continue

        recent_failures = [
            failure
            for failure in failures_by_ip[source_ip]
            if (
                timedelta(0)
                <= timestamp - failure["timestamp"]
                <= CORRELATION_WINDOW
            )
        ]

        if len(recent_failures) < FAILURE_THRESHOLD:
            continue

        # Report each successful event only once.
        if event["index"] in correlated_successes:
            continue

        correlated_successes.add(event["index"])

        findings.append({
            "type": "successful_login_after_failures",
            "source_ip": source_ip,
            "username": event["username"],
            "failed_attempts": len(recent_failures),
            "successful_login_timestamp": (
                timestamp.isoformat()
            ),
            "severity": "high",
            "description": (
                f"Successful login from {source_ip} "
                f"after {len(recent_failures)} failed "
                f"attempts within 15 minutes. "
                f"Potential account compromise; "
                f"authorization is not confirmed."
            ),
            "evidence_event_indices": [
                failure["index"]
                for failure in recent_failures
            ] + [event["index"]],
            "recommended_actions": [
                "Verify whether the login was authorized",
                "Review activity after the successful login",
                "Investigate the source IP and account",
                "Revoke suspicious sessions if confirmed",
                "Reset affected credentials if warranted",
                "Enforce MFA and SSH access controls",
            ],
        })

    # Existing detection: repeated failures.
    for source_ip, count in failed_logins_by_ip.items():
        if count >= FAILURE_THRESHOLD:
            findings.append({
                "type": "repeated_login_failures",
                "source_ip": source_ip,
                "count": count,
                "severity": "medium",
                "description": (
                    f"{count} failed logins detected "
                    f"from {source_ip}"
                ),
                "evidence_event_indices": [
                    event["index"]
                    for event in parsed_events
                    if (
                        event["event_type"]
                        == "login_failure"
                        and event["source_ip"]
                        == source_ip
                    )
                ],
            })

    # Existing malware detection.
    if event_counts["malware_detected"] > 0:
        findings.append({
            "type": "malware_detection",
            "count": event_counts["malware_detected"],
            "severity": "high",
            "description": (
                "Malware detection events observed"
            ),
            "evidence_event_indices": [
                event["index"]
                for event in parsed_events
                if event["event_type"]
                == "malware_detected"
            ],
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
