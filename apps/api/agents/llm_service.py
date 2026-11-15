
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class OpenAILLMService:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0,
            max_retries=2,
        )

    async def ask(self, question: str) -> str:
        response = await self.client.responses.create(
            model=self.model,
            instructions=(
                "You are SecureAgent AI, a cybersecurity "
                "research assistant. Provide accurate, "
                "clear and evidence-based explanations. "
                "Never invent evidence or claim to have "
                "accessed systems you have not accessed."
            ),
            input=question,
            max_output_tokens=300,
            store=False,
        )

        return response.output_text
