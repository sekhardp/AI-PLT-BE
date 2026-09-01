from typing import Any, AsyncGenerator, Dict, List

from fastapi import Depends

from app.clients.agent_client import AgentClient, get_agent_client


class AgentService:
    """
    Business service layer managing agent integrations.
    """

    def __init__(self, client: AgentClient):
        self.client = client

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents from downstream agent service."""
        return await self.client.list_agents()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Fetch details of a specific agent."""
        return await self.client.get_agent(agent_id)

    async def execute_agent_non_streaming(
        self,
        agent_id: str | None,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """Run non-streaming execution against downstream agent."""
        return await self.client.execute_non_streaming(agent_id, prompt, chat_history=chat_history)

    async def execute_agent_streaming(
        self,
        agent_id: str | None,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Run streaming execution against downstream agent."""
        async for chunk in self.client.execute_streaming(agent_id, prompt, chat_history=chat_history):
            yield chunk


def get_agent_service(client: AgentClient = Depends(get_agent_client)) -> AgentService:
    """Dependency injection helper for AgentService."""
    return AgentService(client)
