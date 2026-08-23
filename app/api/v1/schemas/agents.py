from pydantic import BaseModel


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    type: str
    status: str
    description: str
    capabilities: list[str]


class AgentListResponse(BaseModel):
    agents: list[AgentInfo]
    total: int


__all__ = ["AgentInfo", "AgentListResponse"]
