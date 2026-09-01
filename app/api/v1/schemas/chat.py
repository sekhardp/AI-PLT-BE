from pydantic import BaseModel


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
    user_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage


__all__ = ["ChatMessage", "ChatRequest", "ChatResponse"]
