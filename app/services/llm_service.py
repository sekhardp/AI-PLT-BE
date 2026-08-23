import asyncio
import random
from typing import AsyncGenerator

from fastapi import Depends

from app.clients.llm_client import LLMClient, get_llm_client
from app.core.settings import app_settings

STUB_RESPONSES = [
    "I'm the Multi-Agent Orchestrator. I've received your query and I'm routing it to the most suitable agent in the framework.",
    "Based on your request, I'm engaging the RAG Agent to search through the vector store for relevant context. This ensures my response is grounded in your enterprise data.",
    "I've analyzed your prompt and identified it as a data analysis task. Dispatching to AI Agent 2 which specializes in data processing and analytics.",
    "The MCP Server has retrieved the relevant tools needed to fulfill your request. Processing your query through the agent pipeline now.",
    "Your query has been processed through the multi-agent framework. The Orchestrator coordinated between AI Agent 1 and the RAG Agent to synthesize this comprehensive response.",
    "I'm connected to the local LLM inference engine (gpt-oss-120B on GCP GKE). Generating a response tailored to your enterprise context...",
]


class LLMService:
    """
    LLM service layer delegating to an external LLM client when configured,
    or fallback to a local developer stub response.
    """

    def __init__(self, client: LLMClient):
        self.client = client
        self.provider = app_settings.llm_settings.PROVIDER
        self.external_url = app_settings.llm_settings.EXTERNAL_LLM_URL

    async def generate_response(self, prompt: str) -> str:
        """Return a full response from external LLM if configured, otherwise stub."""
        if self.external_url and self.provider != "stub":
            return await self.client.generate(prompt)

        # Fallback stub
        await asyncio.sleep(0.8)
        base = random.choice(STUB_RESPONSES)
        return f"{base}\n\n> **Your query:** {prompt}"

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens from external LLM if configured, otherwise stub stream."""
        if self.external_url and self.provider != "stub":
            async for token in self.client.stream(prompt):
                yield token
            return

        # Fallback stub streaming
        base = random.choice(STUB_RESPONSES)
        full = f"{base}\n\n> **Your query:** {prompt}"

        words = full.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield token
            await asyncio.sleep(random.uniform(0.03, 0.08))


def get_llm_service(client: LLMClient = Depends(get_llm_client)) -> LLMService:
    """Dependency injection helper for LLMService."""
    return LLMService(client)
