
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.rag.retriever import retrieve_chunks


@pytest.mark.asyncio
async def test_rejects_empty_query():
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await retrieve_chunks(
            db=None,
            user_id=1,
            query="   ",
        )


@pytest.mark.asyncio
async def test_rejects_invalid_top_k():
    with pytest.raises(ValueError, match="top_k"):
        await retrieve_chunks(
            db=None,
            user_id=1,
            query="What happened?",
            top_k=100,
        )


@pytest.mark.asyncio
async def test_invalid_query_does_not_call_embedding_api():
    with patch(
        "apps.api.rag.retriever.generate_embedding",
        new_callable=AsyncMock,
    ) as mock_embedding:
        with pytest.raises(ValueError):
            await retrieve_chunks(
                db=None,
                user_id=1,
                query="",
            )

        mock_embedding.assert_not_awaited()
