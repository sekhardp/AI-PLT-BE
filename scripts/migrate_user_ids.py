import asyncio
import logging
from sqlalchemy import select, text
from app.db.session import AsyncSessionLocal
from app.db.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    async with AsyncSessionLocal() as session:
        # 1. Fetch all users
        result = await session.scalars(select(User))
        users = list(result.all())
        logger.info("Found %d registered users to migrate", len(users))

        for user in users:
            uid_str = str(user.id)
            email = user.email.lower().strip()

            # Migrate chat_threads
            r1 = await session.execute(
                text("UPDATE chat_threads SET user_id = :uid WHERE LOWER(user_id) = :email"),
                {"uid": uid_str, "email": email}
            )
            if r1.rowcount > 0:
                logger.info("Updated %d chat_threads for %s -> user_id=%s", r1.rowcount, email, uid_str)

            # Migrate feedback
            r2 = await session.execute(
                text("UPDATE feedback SET user_id = :uid WHERE LOWER(user_id) = :email"),
                {"uid": uid_str, "email": email}
            )
            if r2.rowcount > 0:
                logger.info("Updated %d feedback records for %s -> user_id=%s", r2.rowcount, email, uid_str)

            # Migrate user_documents
            r3 = await session.execute(
                text("UPDATE user_documents SET user_id = :uid WHERE LOWER(user_id) = :email"),
                {"uid": uid_str, "email": email}
            )
            if r3.rowcount > 0:
                logger.info("Updated %d user_documents for %s -> user_id=%s", r3.rowcount, email, uid_str)

        await session.commit()
        logger.info("Database migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate())
