import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.settings import app_settings

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLMClient errors."""
    pass


class LLMClient:
    """
    HTTP client for interacting with the configured external LLM endpoint.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or app_settings.llm_settings.EXTERNAL_LLM_URL
        self.api_key = api_key or app_settings.llm_settings.EXTERNAL_LLM_API_KEY

    async def generate(self, prompt: str) -> str:
        """Call the external LLM non-streaming endpoint and return the text."""
        if not self.base_url:
            raise LLMClientError("external_llm_url is not configured")

        payload = {"prompt": prompt}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Accept either {"text": "..."} or {"response": "..."} or fallback to raw response
                return data.get("text") or data.get("response") or json.dumps(data)
            except httpx.HTTPError as e:
                logger.error("External LLM generation failed: %s", e)
                raise LLMClientError(f"External LLM generation failed: {e}") from e

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Call the external LLM streaming endpoint and yield tokens as they arrive."""
        if not self.base_url:
            raise LLMClientError("external_llm_url is not configured")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=None) as client, client.stream(
                "POST", self.base_url, json={"prompt": prompt}, headers=headers
            ) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")

                # Server-Sent Events (SSE)
                if "text/event-stream" in content_type:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            payload = line[len("data:") :].strip()
                            try:
                                obj = json.loads(payload)
                                token = obj.get("token") or obj.get("text") or payload
                            except Exception:
                                token = payload
                            yield token

                # Fallback: newline-delimited JSON objects or plain text chunks
                else:
                    buffer = ""
                    async for chunk in resp.aiter_text():
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                                token = obj.get("token") or obj.get("text") or line
                            except Exception:
                                token = line
                            yield token
                    if buffer:
                        yield buffer
        except httpx.HTTPError as e:
            logger.error("External LLM streaming failed: %s", e)
            raise LLMClientError(f"External LLM streaming failed: {e}") from e


def get_llm_client() -> LLMClient:
    """Dependency injection helper for LLMClient."""
    return LLMClient()
