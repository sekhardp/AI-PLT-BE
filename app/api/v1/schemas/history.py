from pydantic import BaseModel

from app.api.v1.schemas.chat import ChatMessage


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    last_message: str
    created_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionDetailResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


__all__ = [
    "ChatMessage",
    "SessionDetailResponse",
    "SessionListResponse",
    "SessionSummary",
]
