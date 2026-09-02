import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal, engine, get_db_session

logger = logging.getLogger(__name__)

rag_engine = engine
AsyncRagSession = AsyncSessionLocal


async def get_rag_db() -> AsyncGenerator[AsyncSession, None]:
    """Unified dependency provider for database sessions (aliased to get_db_session)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
