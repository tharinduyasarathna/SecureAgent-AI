
import pytest

from apps.api.rag.chunker import chunk_text


def test_empty_document():
    assert chunk_text("") == []


def test_short_document():
    assert chunk_text("Hello RAG") == ["Hello RAG"]


def test_overlapping_chunks():
    text = "ABCDEFGHIJ"

    result = chunk_text(
        text,
        chunk_size=6,
        overlap=2,
    )

    assert result == [
        "ABCDEF",
        "EFGHIJ",
    ]


def test_invalid_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("test", chunk_size=0)


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("test", chunk_size=10, overlap=10)
