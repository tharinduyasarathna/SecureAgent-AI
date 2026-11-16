
import json
from pathlib import Path


DATASET_PATH = (
    Path(__file__).resolve().parent
    / "multi_document_cases.json"
)


def load_cases():
    with DATASET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def test_unique_case_ids():
    cases = load_cases()
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))


def test_each_case_has_multiple_documents():
    for case in load_cases():
        assert len(case["documents"]) >= 2


def test_documents_have_required_fields():
    for case in load_cases():
        for document in case["documents"]:
            assert document["filename"]
            assert document["content"]


def test_questions_reference_incidents():
    for case in load_cases():
        assert case["incident"] in case["question"]


def test_attack_markers_exist():
    for case in load_cases():
        assert any(
            case["forbidden_output"] in document["content"]
            for document in case["documents"]
        )
