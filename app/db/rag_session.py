import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import app_settings

logger = logging.getLogger(__name__)

import os
# Cloud SQL pgvector connection URL
rag_db_url = os.environ.get("RAG_DB_URL") or "postgresql+psycopg://postgres:W0uld_Y0u_C0nn3ct_M3@35.184.111.56:5432/postgres" 

if rag_db_url.startswith("postgresql://"):
    rag_db_url = rag_db_url.replace("postgresql://", "postgresql+psycopg://")
elif rag_db_url.startswith("sqlite:///"):
    rag_db_url = rag_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

rag_engine_kwargs = {"future": True}
if "sqlite" in rag_db_url:
    rag_engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    rag_engine_kwargs["pool_pre_ping"] = True
    rag_engine_kwargs["pool_size"] = 5
    rag_engine_kwargs["max_overflow"] = 10
    rag_engine_kwargs["pool_timeout"] = 10

rag_engine = create_async_engine(rag_db_url, **rag_engine_kwargs)

AsyncRagSession = sessionmaker(
    rag_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_rag_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for RAG database sessions."""
    async with AsyncRagSession() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
