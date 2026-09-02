import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import delete, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.chat import ChatMessage
from app.api.v1.schemas.feedback import FeedbackRequest
from app.api.v1.schemas.history import SessionSummary
from app.db.models import ChatMessage as ChatMessageModel, ChatThread, Feedback as FeedbackModel
from app.db.session import get_db_session
from app.services.user_service import user_service

logger = logging.getLogger(__name__)


class ChatService:
    """
    Database operations wrapper for managing chat threads, messages, and user feedback.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_or_create_thread(self, session_id: str, user_id: Optional[str] = None) -> ChatThread:
        user_uuid: Optional[uuid.UUID] = None
        if user_id:
            user = await user_service.resolve_user(user_id, self.session)
            if user:
                user_uuid = user.id

        result = await self.session.scalar(
            select(ChatThread).where(ChatThread.session_id == session_id)
        )
        if result:
            if user_uuid and not result.user_id:
                result.user_id = user_uuid
                await self.session.flush()
            return result

        thread = ChatThread(
            session_id=session_id,
            user_id=user_uuid,
            title="New Conversation",
            message_count=0,
            total_tokens=0,
        )
        self.session.add(thread)
        await self.session.flush()
        return thread

    async def add_messages(
        self,
        session_id: str,
        messages: List[ChatMessage],
        user_id: Optional[str] = None,
    ) -> None:
        """Save a list of chat messages and update thread summary counters."""
        thread = await self._get_or_create_thread(session_id, user_id)
        tokens_added = 0

        for message in messages:
            msg_tokens = message.tokens or 0
            tokens_added += msg_tokens
            
            db_message = ChatMessageModel(
                thread_id=thread.id,
                role=message.role,
                content=message.content,
                message_id=message.message_id or str(uuid.uuid4()),
                model=message.model,
                tokens_prompt=msg_tokens if message.role == "user" else 0,
                tokens_completion=msg_tokens if message.role == "assistant" else 0,
                total_tokens=msg_tokens,
                routed_to=message.routed_to,
                complexity_score=message.complexity_score,
            )
            self.session.add(db_message)

        # Update fast denormalized sidebar counters on thread
        thread.message_count += len(messages)
        thread.total_tokens += tokens_added
        if messages:
            last_text = messages[-1].content
            thread.last_message_preview = (last_text[:250] + "...") if len(last_text) > 250 else last_text

        await self.session.commit()

    async def get_messages(self, session_id: str, user_id: Optional[str] = None) -> List[ChatMessage]:
        """Fetch all messages associated with a specific session ID."""
        query = select(ChatThread).options(selectinload(ChatThread.messages)).where(ChatThread.session_id == session_id)
        
        if user_id:
            is_admin = await user_service.is_admin_user(user_id, self.session)
            if not is_admin:
                user = await user_service.resolve_user(user_id, self.session)
                if user:
                    query = query.where(or_(ChatThread.user_id == user.id, ChatThread.user_id == None))

        result = await self.session.scalar(query)
        if not result:
            return []
        return [
            ChatMessage(
                role=message.role,
                content=message.content,
                timestamp=message.created_at.isoformat() if message.created_at else None,
                message_id=message.message_id,
                model=message.model,
                tokens=message.total_tokens or 0,
                routed_to=message.routed_to,
                complexity_score=message.complexity_score,
            )
            for message in result.messages
        ]

    async def list_sessions(self, user_id: Optional[str] = None) -> List[SessionSummary]:
        """List summaries of chat threads using fast indexed columns (no heavy message body scans)."""
        query = select(ChatThread).order_by(ChatThread.created_at.desc())
        
        if user_id:
            is_admin = await user_service.is_admin_user(user_id, self.session)
            if not is_admin:
                user = await user_service.resolve_user(user_id, self.session)
                if user:
                    query = query.where(or_(ChatThread.user_id == user.id, ChatThread.user_id == None))

        result = await self.session.scalars(query)
        threads = result.all()
        
        return [
            SessionSummary(
                session_id=thread.session_id,
                message_count=thread.message_count,
                last_message=thread.last_message_preview or "",
                created_at=thread.created_at.isoformat() if thread.created_at else None,
            )
            for thread in threads
            if thread.message_count > 0 or thread.last_message_preview
        ]

    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """Delete a chat session ensuring user ownership (or admin)."""
        query = delete(ChatThread).where(ChatThread.session_id == session_id)
        if user_id:
            is_admin = await user_service.is_admin_user(user_id, self.session)
            if not is_admin:
                user = await user_service.resolve_user(user_id, self.session)
                if user:
                    query = query.where(or_(ChatThread.user_id == user.id, ChatThread.user_id == None))
        await self.session.execute(query)
        await self.session.commit()

    async def add_feedback(self, feedback: FeedbackRequest) -> None:
        """Save feedback associated with a session/message and user."""
        user_uuid: Optional[uuid.UUID] = None
        if feedback.user_id:
            user = await user_service.resolve_user(feedback.user_id, self.session)
            if user:
                user_uuid = user.id

        self.session.add(
            FeedbackModel(
                feedback_id=feedback.feedback_id or str(uuid.uuid4()),
                session_id=feedback.session_id,
                user_id=user_uuid,
                message_id=feedback.message_id,
                rating=feedback.rating,
                comment=feedback.comment,
            )
        )
        await self.session.commit()

    async def list_feedback(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve feedback filtered by user (admin sees all)."""
        query = select(FeedbackModel).order_by(FeedbackModel.created_at.desc())
        if user_id:
            is_admin = await user_service.is_admin_user(user_id, self.session)
            if not is_admin:
                user = await user_service.resolve_user(user_id, self.session)
                if user:
                    query = query.where(FeedbackModel.user_id == user.id)
        result = await self.session.scalars(query)
        return [
            {
                "feedback_id": row.feedback_id,
                "session_id": row.session_id,
                "message_id": row.message_id,
                "rating": row.rating,
                "comment": row.comment,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.all()
        ]


def get_chat_service(session: AsyncSession = Depends(get_db_session)) -> ChatService:
    """Dependency injection helper for ChatService."""
    return ChatService(session)
