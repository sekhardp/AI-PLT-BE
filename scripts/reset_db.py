"""Script to clean/reset Cloud SQL or local database and apply fresh Alembic migrations."""

import asyncio
import logging
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.settings import app_settings
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reset_db")

TABLES_TO_DROP = [
    "feedback",
    "document_chunks",
    "user_documents",
    "chat_messages",
    "chat_threads",
    "credit_transactions",
    "users",
    "alembic_version",
]


async def reset_database():
    url = app_settings.database_settings.URL
    if url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")

    logger.info("Connecting to target database...")
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        logger.info("Dropping existing tables if any...")
        for table in TABLES_TO_DROP:
            try:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                logger.info("Dropped table: %s", table)
            except Exception as e:
                logger.warning("Could not drop table %s: %s", table, e)

    await engine.dispose()
    logger.info("Initializing clean production schema and running seed data...")
    await init_db()
    logger.info("✅ Database reset and initialized successfully with production schema and HNSW vector index.")


if __name__ == "__main__":
    asyncio.run(reset_database())
