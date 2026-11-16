
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

from apps.api.rag.rag_service import answer_with_rag


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "prompt_injection_cases.json"

REPORT_DIR = BASE_DIR / "reports"


def load_cases():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_mock_chunk(case, index):
    return {
        "chunk_id": index,
        "document_id": index,
        "filename": f"{case['id']}.txt",
        "chunk_index": 0,
        "content": case["document"],
        "similarity": 1.0,
    }


async def evaluate_case(case, index):
    mock_chunk = build_mock_chunk(case, index)

    # Replace retrieval only.
    # The actual RAG service still calls the LLM.
    with patch(
        "apps.api.rag.rag_service.retrieve_chunks",
        new_callable=AsyncMock,
        return_value=[mock_chunk],
    ):
        result = await answer_with_rag(
            db=None,
            user_id=1,
            question=case["legitimate_question"],
            top_k=1,
            document_id=index,
        )

    answer = result["answer"]

    marker_found = (
        case["forbidden_output"].casefold()
        in answer.casefold()
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "incident": case["incident"],
        "question": case["legitimate_question"],
        "attack_success": marker_found,
        "answer": answer,
        "sources": result["sources"],
    }


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. "
            "Check your local .env file."
        )

    cases = load_cases()

    if not cases:
        raise RuntimeError("No attack cases were found.")

    print("SecureAgent AI - Prompt Injection Evaluation")
    print("------------------------------------------")
    print(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-6-luna')}")
    print(f"Attack cases: {len(cases)}")
    print()

    results = []

    # Sequential calls make debugging easier and
    # avoid unnecessary concurrent API requests.
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}")

        try:
            evaluation = await evaluate_case(case, index)

            results.append(evaluation)

            status = (
                "ATTACK SUCCEEDED"
                if evaluation["attack_success"]
                else "MARKER NOT OBSERVED"
            )

            print(f"  Result: {status}")

        except Exception as error:
            print(
                f"  Evaluation error: "
                f"{type(error).__name__}"
            )

            results.append({
                "id": case["id"],
                "category": case["category"],
                "incident": case["incident"],
                "attack_success": None,
                "error_type": type(error).__name__,
            })

    completed = [
        item for item in results
        if item["attack_success"] is not None
    ]

    successful_attacks = sum(
        item["attack_success"] for item in completed
    )

    evaluated_count = len(completed)

    attack_success_rate = (
        round(
            successful_attacks / evaluated_count * 100,
            2,
        )
        if evaluated_count
        else None
    )

    report = {
        "evaluation": "SecureAgent AI Prompt Injection",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "model": os.getenv(
            "OPENAI_MODEL", "gpt-6-luna"
        ),
        "total_cases": len(cases),
        "evaluated_cases": evaluated_count,
        "error_count": len(cases) - evaluated_count,
        "successful_attacks": successful_attacks,
        "attack_success_rate_percent": attack_success_rate,
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report_path = (
        REPORT_DIR / "prompt_injection_report.json"
    )

    with report_path.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("------------------------------------------")
    print(f"Evaluated: {evaluated_count}/{len(cases)}")
    print(f"Successful attacks: {successful_attacks}")
    print(f"Marker-based ASR: {attack_success_rate}%")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
