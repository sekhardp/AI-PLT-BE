import uuid
from typing import Any
import sqlalchemy as sa
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Cross-dialect type helpers (Native Postgres types in production, compatible types in SQLite test suites)
JSONType = sa.JSON().with_variant(JSONB, "postgresql")
UUIDType = sa.Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")
VectorType = sa.Text().with_variant(Vector(768), "postgresql")


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""
    pass


class TimestampMixin:
    """Standard audit timestamps for all database entities."""
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Standardized UUID primary key defaulting to uuid4."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
