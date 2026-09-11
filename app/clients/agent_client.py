import logging
from typing import Any, AsyncGenerator, Dict, List

import httpx

from app.core.settings import app_settings

logger = logging.getLogger(__name__)


class AgentClientError(Exception):
    """Base exception for AgentClient errors."""
    pass


class AgentClient:
    """
    HTTP client for interacting with the downstream Agent Service.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = base_url or app_settings.agent_settings.SERVICE_URL
        self.timeout = timeout or float(app_settings.agent_settings.TIMEOUT_SECONDS)

    async def list_agents(self) -> List[Dict[str, Any]]:
        """Fetch list of agents from the agent service."""
        url = f"{self.base_url}/agents"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("agents", [])
            except httpx.HTTPError as e:
                logger.error("Failed to fetch agents: %s", e)
                raise AgentClientError(f"Failed to fetch agents from agent service: {e}") from e

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Fetch details of a specific agent from the agent service."""
        url = f"{self.base_url}/agents/{agent_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning("Agent '%s' not found: %s", agent_id, e)
                    raise AgentClientError(f"Agent '{agent_id}' not found") from e
                logger.error("Failed to fetch agent '%s': %s", agent_id, e)
                raise AgentClientError(f"Error fetching agent from agent service: {e}") from e
            except httpx.HTTPError as e:
                logger.error("Failed to fetch agent '%s': %s", agent_id, e)
                raise AgentClientError(f"Failed to connect to agent service: {e}") from e

    async def execute_non_streaming(
        self,
        agent_id: str | None,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        model: str | None = None,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """Execute a non-streaming prompt against the agent service."""
        url = f"{self.base_url}/execute"
        payload: dict[str, Any] = {
            "prompt": prompt,
            "agent_id": agent_id,
            "stream": False,
        }
        if model:
            payload["model"] = model
        if session_id:
            payload["session_id"] = session_id
        if chat_history:
            payload["chat_history"] = chat_history
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error("Agent execution failed (non-streaming): %s", e)
                raise AgentClientError(f"Error from agent service: {e}") from e

    async def execute_streaming(
        self,
        agent_id: str | None,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        model: str | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming prompt against the agent service, yielding SSE lines."""
        url = f"{self.base_url}/execute"
        payload: dict[str, Any] = {
            "prompt": prompt,
            "agent_id": agent_id,
            "stream": True,
        }
        if model:
            payload["model"] = model
        if session_id:
            payload["session_id"] = session_id
        if chat_history:
            payload["chat_history"] = chat_history
        try:
            # We don't use standard client timeout here because LLM streams can run for a long time
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        yield line
        except httpx.HTTPError as e:
            logger.error("Agent execution failed (streaming): %s", e)
            raise AgentClientError(f"Error from agent service streaming: {e}") from e

    async def stop_execution(self, session_id: str) -> Dict[str, Any]:
        """Cancel a running execution on the agent service."""
        url = f"{self.base_url}/execute/stop"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json={"session_id": session_id})
                if response.status_code == 200:
                    return response.json()
                return {"status": "error", "session_id": session_id, "detail": response.text}
            except Exception as e:
                logger.warning("Failed to propagate stop request to agent service: %s", e)
                return {"status": "unreachable", "session_id": session_id, "error": str(e)}


def get_agent_client() -> AgentClient:
    """Dependency injection helper for AgentClient."""
    return AgentClient()
