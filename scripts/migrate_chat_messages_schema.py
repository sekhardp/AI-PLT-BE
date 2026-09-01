"""
Migration script to add 'model', 'tokens', 'routed_to', and 'complexity_score' columns
to the 'chat_messages' table in PostgreSQL.
"""
import asyncio
import logging
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    async with AsyncSessionLocal() as session:
        logger.info("Checking chat_messages table schema...")

        # 1. Add model column
        await session.execute(text("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS model VARCHAR(64);
        """))
        logger.info("Added column 'model' (or already exists).")

        # 2. Add tokens column
        await session.execute(text("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS tokens INTEGER DEFAULT 0;
        """))
        logger.info("Added column 'tokens' (or already exists).")

        # 3. Add routed_to column
        await session.execute(text("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS routed_to VARCHAR(32);
        """))
        logger.info("Added column 'routed_to' (or already exists).")

        # 4. Add complexity_score column
        await session.execute(text("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS complexity_score DOUBLE PRECISION;
        """))
        logger.info("Added column 'complexity_score' (or already exists).")

        await session.commit()
        logger.info("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
