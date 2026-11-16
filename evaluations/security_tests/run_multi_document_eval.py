
import asyncio
import json
import os

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

from apps.api.rag.rag_service import answer_with_rag
from evaluations.security_tests.semantic_evaluator import (
    evaluate_answer,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "multi_document_cases.json"

REPORT_PATH = (
    BASE_DIR
    / "reports"
    / "multi_document_report.json"
)


def load_cases():
    with DATASET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def build_mock_chunks(case):
    chunks = []

    for index, document in enumerate(
        case["documents"],
        start=1,
    ):
        chunks.append({
            "chunk_id": index,
            "document_id": index,
            "filename": document["filename"],
            "chunk_index": 0,
            "content": document["content"],
            "similarity": 1.0,
        })

    return chunks


async def evaluate_case(case):
    mock_chunks = build_mock_chunks(case)

    with patch(
        "apps.api.rag.rag_service.retrieve_chunks",
        new_callable=AsyncMock,
    ) as mock_retrieval:

        mock_retrieval.return_value = mock_chunks

        response = await answer_with_rag(
            db=None,
            user_id=1,
            question=case["question"],
            top_k=len(mock_chunks),
        )

    answer = response["answer"]

    security_result = evaluate_answer(
        {
            "id": case["id"],
            "incident": case["incident"],
            "forbidden_output": case["forbidden_output"],
        },
        answer,
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "incident": case["incident"],
        "question": case["question"],
        "answer": answer,
        "sources": response["sources"],
        "security_evaluation": security_result,
    }


async def main():
    cases = load_cases()
    results = []
    errors = []

    print(
        "\nSecureAgent AI - Multi-Document Evaluation"
    )
    print("------------------------------------------")
    print(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-6-luna')}")
    print(f"Attack cases: {len(cases)}\n")

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}")

        try:
            result = await evaluate_case(case)
            results.append(result)

            evaluation = result["security_evaluation"]

            if evaluation["marker_found"]:
                status = "MARKER OBSERVED"
            elif evaluation["unsafe_findings"]:
                status = "UNSAFE PATTERN DETECTED"
            else:
                status = "NO DETECTION"

            print(f"  Result: {status}")

        except Exception as exc:
            errors.append({
                "id": case["id"],
                "error": str(exc),
            })

            print(f"  Error: {exc}")

    evaluated = len(results)

    marker_successes = sum(
        result["security_evaluation"]["marker_found"]
        for result in results
    )

    unsafe_cases = sum(
        bool(
            result["security_evaluation"]["unsafe_findings"]
        )
        for result in results
    )

    report = {
        "evaluation": "SecureAgent AI Multi-Document Security",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "model": os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        "total_cases": len(cases),
        "evaluated_cases": evaluated,
        "error_count": len(errors),
        "marker_based_asr_percent": (
            round(marker_successes / evaluated * 100, 2)
            if evaluated else None
        ),
        "unsafe_pattern_cases": unsafe_cases,
        "results": results,
        "errors": errors,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(report, file, indent=2)

    print("\n------------------------------------------")
    print(f"Evaluated: {evaluated}/{len(cases)}")
    print(f"Errors: {len(errors)}")
    print(f"Marker-based ASR: {report['marker_based_asr_percent']}%")
    print(f"Unsafe-pattern cases: {unsafe_cases}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
