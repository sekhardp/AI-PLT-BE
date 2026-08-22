
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str
    message_id: str | None = None


class ChatRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    agent_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage

