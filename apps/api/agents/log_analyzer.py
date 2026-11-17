from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from typing import Any

ALLOWED_EVENT_TYPES = {
    "login_success", "login_failure", "malware_detected", "network_connection",
    "suspicious_process", "sensitive_file_access", "archive_creation",
    "outbound_data_transfer", "credential_access_alert",
}
AUTHENTICATION_EVENTS = {"login_success", "login_failure"}
FAILURE_THRESHOLD = 5
CORRELATION_WINDOW = timedelta(minutes=15)
ATTACK_CHAIN_WINDOW = timedelta(minutes=60)
MAX_EVENTS = 1000
MAX_FAILED_ATTEMPTS_PER_EVENT = 1000
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
TEXT_FIELDS = (
    "username", "hostname", "process_name", "parent_process", "command_line",
    "file_path", "destination_domain", "protocol", "alert_name", "activity",
)
DETAIL_FIELDS = (
    "hostname", "process_name", "parent_process", "command_line", "file_path",
    "destination_ip", "destination_domain", "protocol", "alert_name", "activity",
    "file_count", "bytes_out",
)
EVENT_RULES = {
    "malware_detected": (
        "malware_detection", "high", "Malware detection event observed; validate the detection.",
        ["Review the malware alert and endpoint telemetry", "Contain the affected system if malicious activity is confirmed"],
    ),
    "suspicious_process": (
        "suspicious_process_execution", "medium", "Suspicious process execution observed.",
        ["Review process command line and parent process", "Determine whether the execution was authorized"],
    ),
    "sensitive_file_access": (
        "sensitive_file_access", "medium", "Sensitive file access activity observed.",
        ["Review accessed files and account permissions", "Verify whether the access was authorized"],
    ),
    "archive_creation": (
        "bulk_archive_creation", "medium", "Archive creation activity observed; bulk collection is not independently established.",
        ["Inspect the archive and creation context", "Review related endpoint and file access activity"],
    ),
    "outbound_data_transfer": (
        "suspicious_outbound_transfer", "medium", "Outbound data transfer observed; exfiltration is not established.",
        ["Inspect proxy logs and destination details", "Verify transferred content and authorization"],
    ),
    "credential_access_alert": (
        "credential_access_alert", "medium", "Potential credential-access behavior flagged; credential theft is not confirmed.",
        ["Review the underlying EDR detection", "Validate whether credential access occurred"],
    ),
}
SUSPICIOUS_TYPES = {
    "suspicious_process", "sensitive_file_access", "archive_creation",
    "outbound_data_transfer", "credential_access_alert",
}


def _validate_ip(value: Any, *, index: int, field: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"Missing {field} at index {index}")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid {field} at index {index}")
    normalized = value.strip()
    try:
        return str(ip_address(normalized))
    except ValueError:
        raise ValueError(f"Invalid {field} at index {index}") from None


def _validate_text(value: Any, *, index: int, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ValueError(f"Invalid {field} at index {index}")
    return value.strip()


def _validate_count(value: Any, *, index: int, field: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid {field} at index {index}")
    return value


def _finding(*, finding_type: str, severity: str, description: str,
             events: list[dict], actions: list[str], **details: Any) -> dict:
    result = {
        "type": finding_type,
        "severity": severity,
        "description": description,
        "evidence_event_indices": sorted({event["index"] for event in events}),
        "recommended_actions": actions,
    }
    result.update(details)
    return result


def _same_identity(left: dict, right: dict) -> bool:
    left_user, right_user = left["username"], right["username"]
    if left_user is not None and right_user is not None:
        return left_user.casefold() == right_user.casefold()
    left_ip, right_ip = left["source_ip"], right["source_ip"]
    return left_ip is not None and right_ip is not None and left_ip == right_ip


def _chain_identity(login: dict, event: dict) -> bool:
    if login["username"] is not None and event["username"] is not None:
        return login["username"].casefold() == event["username"].casefold()
    return (
        login["source_ip"] is not None
        and event["source_ip"] is not None
        and login["source_ip"] == event["source_ip"]
    )


def analyze_security_logs(*, events: list[dict[str, Any]]) -> dict:
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    if len(events) > MAX_EVENTS:
        raise ValueError("Maximum 1000 events allowed")

    event_counts = Counter()
    failed_logins_by_ip = Counter()
    parsed_events = []
    findings = []

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"Event {index} must be an object")
        event_type = event.get("event_type")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Invalid event type at index {index}")
        source_ip = _validate_ip(
            event.get("source_ip"), index=index, field="source_ip",
            required=event_type in AUTHENTICATION_EVENTS,
        )
        destination_ip = _validate_ip(
            event.get("destination_ip"), index=index, field="destination_ip",
        )
        try:
            timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ValueError(f"Invalid timestamp at index {index}") from None
        if timestamp.tzinfo is None:
            raise ValueError(f"Timestamp must include timezone at index {index}")

        parsed = {
            "index": index,
            "timestamp": timestamp.astimezone(timezone.utc),
            "event_type": event_type,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
        }
        for field in TEXT_FIELDS:
            parsed[field] = _validate_text(event.get(field), index=index, field=field)
        for field in ("file_count", "bytes_out"):
            parsed[field] = _validate_count(event.get(field), index=index, field=field)

        failed_attempt_count = 0
        if event_type == "login_failure":
            failed_attempt_count = event.get("failed_attempt_count", 1)
            if (type(failed_attempt_count) is not int or failed_attempt_count < 1
                    or failed_attempt_count > MAX_FAILED_ATTEMPTS_PER_EVENT):
                raise ValueError(f"Invalid failed_attempt_count at index {index}")
            failed_logins_by_ip[source_ip] += failed_attempt_count
        elif event.get("failed_attempt_count") is not None:
            raise ValueError(
                f"failed_attempt_count is only valid for login_failure events at index {index}"
            )
        parsed["failed_attempt_count"] = failed_attempt_count
        event_counts[event_type] += 1
        parsed_events.append(parsed)

    ordered = sorted(parsed_events, key=lambda item: (item["timestamp"], item["index"]))
    failures_by_ip = defaultdict(list)

    for event in ordered:
        if event["event_type"] == "login_failure":
            failures_by_ip[event["source_ip"]].append(event)
            continue
        if event["event_type"] != "login_success":
            continue
        recent = [
            failure for failure in failures_by_ip[event["source_ip"]]
            if timedelta(0) <= event["timestamp"] - failure["timestamp"] <= CORRELATION_WINDOW
            and _same_identity(failure, event)
        ]
        count = sum(item["failed_attempt_count"] for item in recent)
        if count < FAILURE_THRESHOLD:
            continue
        findings.append(_finding(
            finding_type="successful_login_after_failures", severity="high",
            description=(f"Successful login from {event['source_ip']} after {count} failed "
                         "attempts within 15 minutes. Authorization is not confirmed."),
            events=recent + [event], source_ip=event["source_ip"],
            username=event["username"], failed_attempts=count,
            successful_login_timestamp=event["timestamp"].isoformat(),
            actions=["Verify whether the login was authorized", "Review subsequent account activity",
                     "Investigate the source IP and account", "Revoke suspicious sessions if warranted",
                     "Reset affected credentials if warranted", "Enforce MFA and review access controls"],
        ))

    for source_ip, count in failed_logins_by_ip.items():
        if count < FAILURE_THRESHOLD:
            continue
        related = [item for item in parsed_events
                   if item["event_type"] == "login_failure" and item["source_ip"] == source_ip]
        findings.append(_finding(
            finding_type="repeated_login_failures", severity="medium",
            description=f"{count} failed login attempts detected from {source_ip}",
            events=related, source_ip=source_ip, count=count,
            actions=["Investigate the source IP and targeted accounts",
                     "Review authentication logs for additional attempts",
                     "Apply appropriate rate limiting and access controls"],
        ))

    for event in ordered:
        rule = EVENT_RULES.get(event["event_type"])
        if rule is None:
            continue
        finding_type, severity, description, actions = rule
        details = {key: event[key] for key in DETAIL_FIELDS if event.get(key) is not None}
        findings.append(_finding(
            finding_type=finding_type, severity=severity, description=description,
            events=[event], actions=actions,
            source_ip=event["source_ip"], username=event["username"],
            event_timestamp=event["timestamp"].isoformat(), **details,
        ))

    for login in ordered:
        if login["event_type"] != "login_success":
            continue
        subsequent = [
            event for event in ordered
            if event["event_type"] in SUSPICIOUS_TYPES
            and timedelta(0) < event["timestamp"] - login["timestamp"] <= ATTACK_CHAIN_WINDOW
            and _chain_identity(login, event)
        ]
        types = sorted({item["event_type"] for item in subsequent})
        if len(types) < 2:
            continue
        findings.append(_finding(
            finding_type="multi_stage_suspicious_activity", severity="high",
            description=("Multiple categories of suspicious activity followed a successful login "
                         "with a matching account or source IP. Compromise and exfiltration are not established."),
            events=[login] + subsequent, source_ip=login["source_ip"],
            username=login["username"], correlated_event_types=types,
            actions=["Review the full incident timeline", "Verify account and endpoint activity",
                     "Preserve authentication, EDR, and proxy logs",
                     "Investigate potential data staging and transfer",
                     "Confirm whether each activity was authorized"],
        ))

    findings.sort(key=lambda item: (-SEVERITY_RANK[item["severity"]], item["type"],
                                    item["evidence_event_indices"][0]))
    return {
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "failed_login_attempts": sum(failed_logins_by_ip.values()),
        "findings": findings,
        "finding_count": len(findings),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
