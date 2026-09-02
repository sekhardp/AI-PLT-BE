import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType

if TYPE_CHECKING:
    from app.db.models.chat import ChatThread
    from app.db.models.document import UserDocument
    from app.db.models.feedback import Feedback


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User profile, access role, and credit bank balance."""
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("credits >= 0", name="chk_user_credits_non_negative"),
        CheckConstraint("tokens_used >= 0", name="chk_user_tokens_non_negative"),
    )

    username: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    transactions: Mapped[List["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="user", cascade="all, delete-orphan", order_by="CreditTransaction.created_at.desc()"
    )
    threads: Mapped[List["ChatThread"]] = relationship(
        "ChatThread", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[List["UserDocument"]] = relationship(
        "UserDocument", back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="user"
    )


class CreditTransaction(Base, UUIDPrimaryKeyMixin):
    """Immutable financial ledger of credit grants, deductions, and token accounting."""
    __tablename__ = "credit_transactions"
    __table_args__ = (
        Index("idx_credit_tx_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_charged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), default="chat_execution", nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="transactions")
