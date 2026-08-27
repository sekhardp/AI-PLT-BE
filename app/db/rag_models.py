import uuid
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.models import Base


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(64), nullable=False)
    status = Column(String(32), default="indexing", nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("user_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("UserDocument", back_populates="chunks")
