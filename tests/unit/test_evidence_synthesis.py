
import json
from unittest.mock import Mock

import pytest

from apps.api.agents.evidence_synthesis import (
    EvidenceSynthesisError,
    prepare_sources,
    validate_synthesis,
    synthesize_evidence,
)


def sample_sources():
    return [
        {
            "chunk_id": 10,
            "content": (
                "Six failed login attempts from "
                "192.0.2.10."
            ),
        }
    ]


def sample_result():
    return {
        "summary": (
            "Evidence indicates repeated failed logins."
        ),
        "risk_level": "medium",
        "source_ids": [10],
        "limitations": (
            "The source does not establish "
            "whether access was successful."
        ),
    }


# ==================================================
# Existing evidence synthesis tests
# ==================================================


def test_prepare_sources():
    prepared = prepare_sources(sample_sources())

    assert prepared[0]["source_id"] == 10


def test_duplicate_source_rejected():
    sources = sample_sources() * 2

    with pytest.raises(EvidenceSynthesisError):
        prepare_sources(sources)


def test_invalid_source_id_rejected():
    sources = [
        {
            "chunk_id": -1,
            "content": "Synthetic evidence",
        }
    ]

    with pytest.raises(EvidenceSynthesisError):
        prepare_sources(sources)


def test_unapproved_citation_rejected():
    result = sample_result()
    result["source_ids"] = [999]

    with pytest.raises(EvidenceSynthesisError):
        validate_synthesis(result, {10})


def test_extra_output_fields_rejected():
    result = sample_result()
    result["execute_command"] = "delete_logs"

    with pytest.raises(EvidenceSynthesisError):
        validate_synthesis(result, {10})


def test_valid_synthesis_accepted():
    result = sample_result()

    validated = validate_synthesis(
        result,
        {10},
    )

    assert validated["risk_level"] == "medium"


def test_empty_sources_no_model_call():
    client = Mock()

    result = synthesize_evidence(
        client=client,
        model="mock-model",
        request="Investigate logins",
        sources=[],
    )

    assert result["risk_level"] == "unknown"
    client.responses.create.assert_not_called()


def test_model_synthesis():
    client = Mock()

    client.responses.create.return_value.output_text = (
        json.dumps(sample_result())
    )

    result = synthesize_evidence(
        client=client,
        model="mock-model",
        request="Investigate failed logins",
        sources=sample_sources(),
    )

    assert result["source_ids"] == [10]

    call = client.responses.create.call_args.kwargs

    assert call["store"] is False
    assert "tools" not in call


def test_invalid_model_json_rejected():
    client = Mock()

    client.responses.create.return_value.output_text = (
        "not valid json"
    )

    with pytest.raises(EvidenceSynthesisError):
        synthesize_evidence(
            client=client,
            model="mock-model",
            request="Investigate failed logins",
            sources=sample_sources(),
        )


# ==================================================
# A4.4 — Failure recovery and input validation
# ==================================================


def test_openai_api_failure_propagates():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "Synthetic OpenAI API failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic OpenAI API failure",
    ):
        synthesize_evidence(
            client=client,
            model="mock-model",
            request="Investigate failed logins",
            sources=sample_sources(),
        )

    client.responses.create.assert_called_once()


def test_oversized_evidence_is_truncated():
    sources = [
        {
            "chunk_id": 10,
            "content": "A" * 10000,
        }
    ]

    prepared = prepare_sources(sources)

    assert len(prepared[0]["content"]) == 4000
    assert prepared[0]["source_id"] == 10


def test_too_many_sources_rejected():
    sources = [
        {
            "chunk_id": index + 1,
            "content": "Synthetic evidence",
        }
        for index in range(6)
    ]

    with pytest.raises(
        EvidenceSynthesisError,
        match="Too many evidence sources",
    ):
        prepare_sources(sources)


@pytest.mark.parametrize(
    "investigation_request",
    [
        "",
        "   ",
        "A" * 2001,
        None,
    ],
)
def test_invalid_request_rejected_before_model_call(
    investigation_request,
):
    client = Mock()

    with pytest.raises(EvidenceSynthesisError):
        synthesize_evidence(
            client=client,
            model="mock-model",
            request=investigation_request,
            sources=sample_sources(),
        )

    client.responses.create.assert_not_called()


def test_invalid_risk_level_rejected():
    result = sample_result()
    result["risk_level"] = "critical"

    with pytest.raises(EvidenceSynthesisError):
        validate_synthesis(result, {10})


def test_duplicate_citations_rejected():
    result = sample_result()
    result["source_ids"] = [10, 10]

    with pytest.raises(EvidenceSynthesisError):
        validate_synthesis(result, {10})


def test_non_integer_citation_rejected():
    result = sample_result()
    result["source_ids"] = [True]

    with pytest.raises(EvidenceSynthesisError):
        validate_synthesis(result, {10})
