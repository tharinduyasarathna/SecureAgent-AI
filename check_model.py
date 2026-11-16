
# from dotenv import load_dotenv
# from openai import OpenAI

# load_dotenv()

# client = OpenAI()

# response = client.responses.create(
#     model="gpt-6-luna",
#     input="Explain RAG in one sentence.",
#     max_output_tokens=150,
#     store=False,
# )

# print(response.output_text)

# -----------------------------

# import asyncio

# from apps.api.rag.embeddings import generate_embedding


# async def main():
#     text = "A prompt injection attack attempts to manipulate an AI system."

#     embedding = await generate_embedding(text)

#     print("Embedding dimensions:", len(embedding))
#     print("First five values:", embedding[:5])


# if __name__ == "__main__":
#     asyncio.run(main())


# ---------------------------


import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from apps.api.app.database import Base
from apps.api.app.models import User
from apps.api.rag.models import RAGDocument, RAGChunk


def main():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")

    if make_url(database_url).database != "secureagent_test":
        raise RuntimeError("Refusing to initialize a non-test database")

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            actual_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            if actual_database != "secureagent_test":
                raise RuntimeError(
                    f"Unexpected database: {actual_database}"
                )

        # Create only missing tables; never drop existing tables.
        Base.metadata.create_all(bind=engine, checkfirst=True)

        print("Test database schema initialized.")
        print("Tables:", inspect(engine).get_table_names())

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

