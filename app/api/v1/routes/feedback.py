from fastapi import APIRouter, Depends

from app.api.v1.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.chat_service import ChatService, get_chat_service

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Submit rating and optional comments for a chat message."""
    await chat_service.add_feedback(req)
    return FeedbackResponse(feedback_id=req.feedback_id, status="received")


@router.get("")
async def list_feedback(
    chat_service: ChatService = Depends(get_chat_service)
):
    """Retrieve all submitted feedback."""
    feedback = await chat_service.list_feedback()
    return {"feedback": feedback}
