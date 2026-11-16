
import json
from pathlib import Path

from evaluations.security_tests.semantic_evaluator import (
    evaluate_answer,
)

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "prompt_injection_cases.json"
REPORT_PATH = BASE_DIR / "reports" / "prompt_injection_report.json"
OUTPUT_PATH = BASE_DIR / "reports" / "semantic_security_report.json"


def main():
    with DATASET_PATH.open(encoding="utf-8") as file:
        cases = {
            case["id"]: case
            for case in json.load(file)
        }

    with REPORT_PATH.open(encoding="utf-8") as file:
        report = json.load(file)

    results = []

    for item in report["results"]:
        case = cases.get(item["id"])

        if case is None or not isinstance(item.get("answer"), str):
            continue

        evaluation = evaluate_answer(case, item["answer"])

        results.append({
            **evaluation,
            "category": item["category"],
        })

    total = len(results)

    marker_successes = sum(
        result["marker_found"]
        for result in results
    )

    unsafe_cases = sum(
        bool(result["unsafe_findings"])
        for result in results
    )

    cited_cases = sum(
        result["source_cited"]
        for result in results
    )

    incident_coverage = sum(
        result["incident_mentioned"]
        for result in results
    )

    summary = {
        "evaluated_cases": total,
        "marker_based_asr_percent": (
            round(marker_successes / total * 100, 2)
            if total else None
        ),
        "unsafe_pattern_cases": unsafe_cases,
        "citation_presence_percent": (
            round(cited_cases / total * 100, 2)
            if total else None
        ),
        "incident_reference_percent": (
            round(incident_coverage / total * 100, 2)
            if total else None
        ),
    }

    output = {
        "evaluation": "SecureAgent AI Semantic Security",
        "summary": summary,
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    print("\nSecureAgent AI - Semantic Security Evaluation")
    print("---------------------------------------------")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print(f"\nReport saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
