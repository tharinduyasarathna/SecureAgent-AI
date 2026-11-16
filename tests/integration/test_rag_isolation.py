
import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from apps.api.app.models import User
from apps.api.rag.models import RAGChunk, RAGDocument
from apps.api.rag.retriever import retrieve_chunks


# --------------------------------------------------
# Test database configuration
# --------------------------------------------------

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is required. "
        "Configure a dedicated PostgreSQL test database."
    )

# Check the database name parsed from the URL.
database_name = make_url(TEST_DATABASE_URL).database

if database_name != "secureagent_test":
    raise RuntimeError(
        f"Unsafe test database: {database_name!r}. "
        "Expected 'secureagent_test'."
    )

engine = create_engine(TEST_DATABASE_URL)


# --------------------------------------------------
# Safe transaction-based database fixture
# --------------------------------------------------

@pytest.fixture
def db():
    connection = engine.connect()

    try:
        # Verify the actual connected database.
        actual_database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if actual_database != "secureagent_test":
            raise RuntimeError(
                f"Unsafe database connection: "
                f"{actual_database!r}"
            )

        # Outer transaction protects persistent data.
        connection.rollback()
        transaction = connection.begin()

        # Savepoints allow db.commit() inside the test
        # without committing the outer transaction.
        session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            session.close()
            transaction.rollback()

    finally:
        connection.close()


# --------------------------------------------------
# Cross-user RAG document isolation test
# --------------------------------------------------

@pytest.mark.asyncio
async def test_cross_user_document_isolation(db: Session):

    user_a = User(
        email="user_a_test@example.com",
        password_hash="test-only-hash",
    )

    user_b = User(
        email="user_b_test@example.com",
        password_hash="test-only-hash",
    )

    db.add_all([user_a, user_b])
    db.flush()

    document = RAGDocument(
        owner_id=user_a.id,
        filename="private_incident.txt",
    )

    db.add(document)
    db.flush()

    db.add(
        RAGChunk(
            document_id=document.id,
            chunk_index=0,
            content="Confidential incident SEC-TEST-001.",
            embedding=[0.01] * 1536,
        )
    )

    db.commit()

    with patch(
        "apps.api.rag.retriever.generate_embedding",
        new_callable=AsyncMock,
        return_value=[0.01] * 1536,
    ):

        # User A can access their own document.
        owner_results = await retrieve_chunks(
            db=db,
            user_id=user_a.id,
            query="SEC-TEST-001",
            document_id=document.id,
        )

        assert len(owner_results) == 1
        assert owner_results[0]["document_id"] == document.id

        # User B cannot access User A's document.
        attacker_results = await retrieve_chunks(
            db=db,
            user_id=user_b.id,
            query="SEC-TEST-001",
            document_id=document.id,
        )

        assert attacker_results == []

        # User B cannot discover User A's document
        # through general semantic retrieval.
        general_results = await retrieve_chunks(
            db=db,
            user_id=user_b.id,
            query="SEC-TEST-001",
        )

        assert general_results == []
