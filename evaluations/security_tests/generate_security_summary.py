
import json
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def load_report(filename):
    path = REPORTS_DIR / filename

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def main():
    single = load_report("semantic_security_report.json")
    multi = load_report("multi_document_report.json")
    e2e = load_report("e2e_rag_security_report.json")

    assert single["summary"]["evaluated_cases"] == 10
    assert len(single["results"]) == 10

    assert multi["total_cases"] == 3
    assert multi["evaluated_cases"] == 3
    assert multi["error_count"] == 0
    assert len(multi["results"]) == 3

    assert e2e["case"]["id"] == "E2E-001"
    assert len(e2e["sources"]) == 2
    assert {
        source["filename"] for source in e2e["sources"]
    } == {"incident_report.txt", "malicious_notes.txt"}

    single_results = single["results"]
    multi_results = multi["results"]
    e2e_result = e2e["security_evaluation"]

    all_evaluations = [
        *single_results,
        *[
            item["security_evaluation"]
            for item in multi_results
        ],
        e2e_result,
    ]

    total = len(all_evaluations)

    marker_successes = sum(
        bool(item["marker_found"])
        for item in all_evaluations
    )

    unsafe_findings = sum(
        bool(item["unsafe_findings"])
        for item in all_evaluations
    )

    citation_presence = sum(
        bool(item["source_cited"])
        for item in all_evaluations
    )

    summary = {
        "project": "SecureAgent AI",
        "evaluation": "Consolidated RAG Security Evaluation",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "automated_regression_tests_last_reported": 32,
        "single_document_cases": len(single_results),
        "multi_document_cases": len(multi_results),
        "end_to_end_cases": 1,
        "total_evaluated_cases": total,
        "marker_successes": marker_successes,
        "marker_based_asr_percent": (
            round(marker_successes / total * 100, 2)
            if total else None
        ),
        "unsafe_pattern_cases": unsafe_findings,
        "citation_presence_percent": (
            round(citation_presence / total * 100, 2)
            if total else None
        ),
        "limitations": [
            "Small synthetic adversarial dataset",
            "Single model run per scenario",
            "Heuristic unsafe recommendation detection",
            "Synthetic embeddings in database-backed evaluation",
            "Citation presence does not establish factual grounding",
            "Some evaluations use mocked retrieval",
        ],
    }

    output_path = REPORTS_DIR / "security_summary.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\nSecureAgent AI - Consolidated Security Summary")
    print("---------------------------------------------")

    for key, value in summary.items():
        if key != "limitations":
            print(f"{key}: {value}")

    print(f"\nReport saved: {output_path}")


if __name__ == "__main__":
    main()
