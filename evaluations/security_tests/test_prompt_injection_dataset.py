
import json
from pathlib import Path

import pytest

import base64
import binascii
import re


DATASET_PATH = (
    Path(__file__).parent / "prompt_injection_cases.json"
)


@pytest.fixture(scope="module")
def attack_cases():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_attack_dataset_has_unique_ids(attack_cases):
    ids = [case["id"] for case in attack_cases]

    assert len(ids) == len(set(ids))


def test_attack_dataset_has_required_fields(attack_cases):
    required_fields = {
        "id",
        "category",
        "incident",
        "legitimate_question",
        "document",
        "forbidden_output",
    }

    for case in attack_cases:
        assert required_fields.issubset(case)



def test_attack_payloads_contain_markers(attack_cases):
    for case in attack_cases:
        marker = case["forbidden_output"]
        document = case["document"]

        if case["category"] == "encoded_instruction":
            # Extract Base64-encoded tokens from the document.
            encoded_candidates = re.findall(
                r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])",
                document,
            )

            decoded_markers = []

            for candidate in encoded_candidates:
                try:
                    decoded = base64.b64decode(
                        candidate,
                        validate=True,
                    ).decode("utf-8")

                    decoded_markers.append(decoded)

                except (ValueError, UnicodeDecodeError, binascii.Error):
                    continue

            assert marker in decoded_markers, (
                f"Encoded marker not found in {case['id']}"
            )

        else:
            assert marker in document, (
                f"Marker not found in {case['id']}"
            )



def test_attack_questions_reference_incidents(attack_cases):
    for case in attack_cases:
        assert case["incident"] in case["legitimate_question"]


def test_attack_dataset_has_multiple_categories(attack_cases):
    categories = {
        case["category"] for case in attack_cases
    }

    assert len(categories) >= 4
