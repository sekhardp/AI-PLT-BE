import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Double, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType

if TYPE_CHECKING:
    from app.db.models.feedback import Feedback
    from app.db.models.user import User


class ChatThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Conversational session containing messages and summary telemetry."""
    __tablename__ = "chat_threads"
    __table_args__ = (
        Index("idx_chat_threads_user_created", "user_id", "created_at"),
    )

    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_message_preview: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="threads")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
    )
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback",
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual conversational prompt or model response turn."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_messages_thread_created", "thread_id", "created_at"),
        Index("idx_chat_messages_message_id", "message_id"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    routed_to: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    complexity_score: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)

    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="message")
