import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType, VectorType

if TYPE_CHECKING:
    from app.db.models.user import User


class UserDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User-uploaded document artifact metadata and ingestion status."""
    __tablename__ = "user_documents"
    __table_args__ = (
        Index("idx_user_docs_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="indexing", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index.asc()",
    )


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantically partitioned document chunk with dense vector embedding for RAG."""
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("idx_doc_chunks_doc_index", "document_id", "chunk_index"),
        Index("idx_doc_chunks_user_doc", "user_id", "document_id"),
        Index(
            "idx_doc_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(VectorType, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    document: Mapped["UserDocument"] = relationship("UserDocument", back_populates="chunks")
