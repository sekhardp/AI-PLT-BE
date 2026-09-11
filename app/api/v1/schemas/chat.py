from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str
    message_id: str | None = None
    model: str | None = None
    tokens: int | None = None
    routed_to: str | None = None
    complexity_score: float | None = None


class ChatRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    agent_id: str | None = None
    model: str | None = None
    user_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage


class StopChatRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to stop execution for")


class ModelTokenItem(BaseModel):
    model: str
    display_name: str
    tier: str  # 'local' | 'frontier'
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    message_count: int
    percentage: float


class TierTokenSummary(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    message_count: int
    percentage: float


class TokenStatsResponse(BaseModel):
    total_tokens: int
    total_queries: int
    by_model: List[ModelTokenItem]
    by_tier: dict[str, TierTokenSummary]


__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "StopChatRequest",
    "ModelTokenItem",
    "TierTokenSummary",
    "TokenStatsResponse",
]
