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

    async def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Fetch all messages associated with a specific session ID."""
        result = await self.session.scalar(
            select(ChatThread)
            .options(selectinload(ChatThread.messages))
            .where(ChatThread.session_id == session_id)
        )
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

    async def list_sessions(self) -> List[SessionSummary]:
        """List summaries of all chat threads order by creation date desc."""
        result = await self.session.scalars(
            select(ChatThread)
            .options(selectinload(ChatThread.messages))
            .order_by(ChatThread.created_at.desc())
        )
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

    async def delete_session(self, session_id: str) -> None:
        """Delete a chat session and all cascading messages."""
        await self.session.execute(
            delete(ChatThread).where(ChatThread.session_id == session_id)
        )
        await self.session.commit()

    async def add_feedback(self, feedback: FeedbackRequest) -> None:
        """Save feedback associated with a session/message."""
        self.session.add(
            FeedbackModel(
                feedback_id=feedback.feedback_id,
                session_id=feedback.session_id,
                message_id=feedback.message_id,
                rating=feedback.rating,
                comment=feedback.comment,
            )
        )
        await self.session.commit()

    async def list_feedback(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded user feedback submissions."""
        result = await self.session.scalars(select(FeedbackModel))
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
