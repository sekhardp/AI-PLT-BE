from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.agents import AgentInfo, AgentListResponse
from app.clients.agent_client import AgentClientError
from app.services.agent_service import AgentService, get_agent_service

router = APIRouter()


@router.get("", response_model=AgentListResponse)
async def list_agents(service: AgentService = Depends(get_agent_service)):
    """List all available agents registered in downstream agent service."""
    try:
        agents_data = await service.list_agents()
        agents = []
        for agent_data in agents_data:
            agents.append(
                AgentInfo(
                    agent_id=agent_data["agent_id"],
                    name=agent_data["name"],
                    description=agent_data.get("description", ""),
                    capabilities=agent_data.get("capabilities", []),
                    status=agent_data.get("status", "active"),
                    type="orchestrator"
                    if "orchestrator" in agent_data["agent_id"]
                    else "ai-agent",
                )
            )
        return AgentListResponse(agents=agents, total=len(agents))
    except AgentClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str, service: AgentService = Depends(get_agent_service)):
    """Retrieve details of a single agent."""
    try:
        agent_data = await service.get_agent(agent_id)
        return AgentInfo(
            agent_id=agent_data["agent_id"],
            name=agent_data["name"],
            description=agent_data.get("description", ""),
            capabilities=agent_data.get("capabilities", []),
            status=agent_data.get("status", "active"),
            type="orchestrator"
            if "orchestrator" in agent_data["agent_id"]
            else "ai-agent",
        )
    except AgentClientError as e:
        status_code = 404 if "not found" in str(e).lower() else 502
        raise HTTPException(status_code=status_code, detail=str(e))
