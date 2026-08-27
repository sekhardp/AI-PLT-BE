from typing import Any, Dict, List

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.chat import ChatMessage
from app.api.v1.schemas.feedback import FeedbackRequest
from app.api.v1.schemas.history import SessionSummary
from app.db.models import ChatMessage as ChatMessageModel
from app.db.models import ChatThread
from app.db.models import Feedback as FeedbackModel
from app.db.session import get_db_session


class ChatService:
    """
    Database operations wrapper for managing chat threads, messages, and user feedback.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_or_create_thread(self, session_id: str, user_id: str | None = None) -> ChatThread:
        result = await self.session.scalar(
            select(ChatThread).where(ChatThread.session_id == session_id)
        )
        if result:
            if user_id and not result.user_id:
                result.user_id = user_id
                await self.session.flush()
            return result

        thread = ChatThread(session_id=session_id, user_id=user_id)
        self.session.add(thread)
        await self.session.flush()
        return thread

    async def add_messages(
        self,
        session_id: str,
        messages: List[ChatMessage],
        user_id: str | None = None,
    ) -> None:
        """Save a list of chat messages to the database thread."""
        thread = await self._get_or_create_thread(session_id, user_id)
        for message in messages:
            db_message = ChatMessageModel(
                thread_id=thread.id,
                role=message.role,
                content=message.content,
                message_id=message.message_id,
            )
            self.session.add(db_message)
        await self.session.commit()

    async def get_messages(self, session_id: str, user_id: str | None = None) -> List[ChatMessage]:
        """Fetch all messages associated with a specific session ID."""
        query = select(ChatThread).options(selectinload(ChatThread.messages)).where(ChatThread.session_id == session_id)
        if user_id and user_id != "admin@example.com":
            query = query.where(or_(ChatThread.user_id == user_id, ChatThread.user_id == None))
        result = await self.session.scalar(query)
        if not result:
            return []
        return [
            ChatMessage(
                role=message.role,
                content=message.content,
                timestamp=message.created_at.isoformat(),
                message_id=message.message_id,
            )
            for message in result.messages
        ]

    async def list_sessions(self, user_id: str | None = None) -> List[SessionSummary]:
        """List summaries of chat threads filtered by user (admin sees all)."""
        query = select(ChatThread).options(selectinload(ChatThread.messages)).order_by(ChatThread.created_at.desc())
        if user_id and user_id != "admin@example.com":
            query = query.where(ChatThread.user_id == user_id)
        result = await self.session.scalars(query)
        sessions = []
        for thread in result.unique().all():
            if not thread.messages:
                continue
            last_message = thread.messages[-1]
            last_text = last_message.content
            if len(last_text) > 80:
                last_text = last_text[:80] + "..."
            sessions.append(
                SessionSummary(
                    session_id=thread.session_id,
                    message_count=len(thread.messages),
                    last_message=last_text,
                    created_at=thread.created_at.isoformat(),
                )
            )
        return sessions

    async def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        """Delete a chat session ensuring user ownership (or admin)."""
        query = delete(ChatThread).where(ChatThread.session_id == session_id)
        if user_id and user_id != "admin@example.com":
            query = query.where(or_(ChatThread.user_id == user_id, ChatThread.user_id == None))
        await self.session.execute(query)
        await self.session.commit()

    async def add_feedback(self, feedback: FeedbackRequest) -> None:
        """Save feedback associated with a session/message and user."""
        self.session.add(
            FeedbackModel(
                feedback_id=feedback.feedback_id,
                session_id=feedback.session_id,
                user_id=feedback.user_id,
                message_id=feedback.message_id,
                rating=feedback.rating,
                comment=feedback.comment,
            )
        )
        await self.session.commit()

    async def list_feedback(self, user_id: str | None = None) -> List[Dict[str, Any]]:
        """Retrieve feedback filtered by user (admin sees all)."""
        query = select(FeedbackModel).order_by(FeedbackModel.created_at.desc())
        if user_id and user_id != "admin@example.com":
            query = query.where(FeedbackModel.user_id == user_id)
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
