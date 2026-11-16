
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.auth_dependencies import get_current_user
from apps.api.app.database import get_db
from apps.api.app.models import User


class FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


@pytest.fixture
def client():
    # Disable database initialization during API tests.
    with patch(
        "apps.api.app.main.Base.metadata.create_all"
    ):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        (
            "/rag/search",
            {"query": "incident report"},
        ),
        (
            "/rag/ask",
            {"question": "What happened?"},
        ),
    ],
)
def test_missing_jwt_is_rejected(
    client,
    endpoint,
    payload,
):
    response = client.post(endpoint, json=payload)

    assert response.status_code in (401, 403)


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        (
            "/rag/search",
            {"query": "incident report"},
        ),
        (
            "/rag/ask",
            {"question": "What happened?"},
        ),
    ],
)
def test_invalid_jwt_is_rejected(
    client,
    endpoint,
    payload,
):
    response = client.post(
        endpoint,
        json=payload,
        headers={
            "Authorization": "Bearer invalid.jwt.token",
        },
    )

    assert response.status_code == 401


def test_authenticated_search_uses_user_identity(client):
    fake_user = FakeUser(user_id=2)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = lambda: None

    with patch(
        "apps.api.routes.retrieval.retrieve_chunks",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_retrieve:

        response = client.post(
            "/rag/search",
            json={
                "query": "private incident",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        assert response.json()["results_count"] == 0

        assert mock_retrieve.await_args.kwargs["user_id"] == 2


def test_authenticated_rag_uses_user_identity(client):
    fake_user = FakeUser(user_id=2)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = lambda: None

    with patch(
        "apps.api.routes.rag_chat.answer_with_rag",
        new_callable=AsyncMock,
        return_value={
            "answer": "No relevant documents were found.",
            "sources": [],
        },
    ) as mock_answer:

        response = client.post(
            "/rag/ask",
            json={
                "question": "Summarize document 2",
                "document_id": 2,
            },
        )

        assert response.status_code == 200
        assert response.json()["sources"] == []

        kwargs = mock_answer.await_args.kwargs

        assert kwargs["user_id"] == 2
        assert kwargs["document_id"] == 2
