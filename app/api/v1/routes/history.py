from typing import Optional
from fastapi import APIRouter, Depends

from app.api.v1.schemas.history import SessionDetailResponse, SessionListResponse
from app.services.chat_service import ChatService, get_chat_service

router = APIRouter()


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = None,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Retrieve summaries of recorded chat sessions filtered by user."""
    sessions = await chat_service.list_sessions(user_id=user_id)
    return SessionListResponse(sessions=sessions)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    user_id: Optional[str] = None,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get the full message history for a specific session."""
    messages = await chat_service.get_messages(session_id, user_id=user_id)
    return SessionDetailResponse(session_id=session_id, messages=messages)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: Optional[str] = None,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Delete a chat session and its complete message logs."""
    await chat_service.delete_session(session_id, user_id=user_id)
    return {"deleted": session_id}
