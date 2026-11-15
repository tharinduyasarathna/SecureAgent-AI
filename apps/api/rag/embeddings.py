
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dimensional embedding for a text passage."""

    if not text.strip():
        raise ValueError("Cannot embed empty text")

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    return response.data[0].embedding
