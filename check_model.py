
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



import asyncio

from apps.api.rag.embeddings import generate_embedding


async def main():
    text = "A prompt injection attack attempts to manipulate an AI system."

    embedding = await generate_embedding(text)

    print("Embedding dimensions:", len(embedding))
    print("First five values:", embedding[:5])


if __name__ == "__main__":
    asyncio.run(main())
