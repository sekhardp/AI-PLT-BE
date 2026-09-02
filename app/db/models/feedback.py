import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UUIDPrimaryKeyMixin, UUIDType

if TYPE_CHECKING:
    from app.db.models.chat import ChatMessage, ChatThread
    from app.db.models.user import User


class Feedback(Base, UUIDPrimaryKeyMixin):
    """User qualitative feedback and RLHF rating on model responses."""
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_feedback_rating_range"),
        Index("idx_feedback_session_id", "session_id"),
        Index("idx_feedback_user_id", "user_id"),
        Index("idx_feedback_rating", "rating"),
    )

    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_threads.session_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("chat_messages.message_id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="feedbacks")
    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="feedbacks")
    message: Mapped[Optional["ChatMessage"]] = relationship("ChatMessage", back_populates="feedbacks")
