import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import app_settings
from app.db.models import Base, ChatMessage, ChatThread, Feedback, User

logger = logging.getLogger(__name__)

database_url = app_settings.database_settings.URL

# Automatically resolve sync DB URLs to their async equivalents for SQLAlchemy async compatibility
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://")

# Configure appropriate engine options depending on database dialect
engine_kwargs = {"echo": app_settings.database_settings.ECHO, "future": True}

if "sqlite" in database_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Connection pool options for production databases (Cloud SQL)
    engine_kwargs["pool_size"] = max(app_settings.database_settings.POOL_SIZE, 10)
    engine_kwargs["max_overflow"] = max(app_settings.database_settings.MAX_OVERFLOW, 20)
    engine_kwargs["pool_pre_ping"] = app_settings.database_settings.POOL_PRE_PING
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_timeout"] = 15

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=app_settings.database_settings.EXPIRE_ON_COMMIT,
    autocommit=False,
    autoflush=app_settings.database_settings.AUTO_FLUSH,
)


async def get_db_session():
    """FastAPI dependency to retrieve an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Standard alias for get_db_session
get_db = get_db_session


async def seed_db():
    """Seed the database with sample data if it's empty."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ChatThread).limit(1))
        if result.scalars().first() is not None:
            return

        logger.info("Seeding database with sample chat and feedback data...")
        
        # Check or create seed user
        user_res = await session.execute(select(User).where(User.email == "seed-user@example.com"))
        seed_user = user_res.scalars().first()
        if not seed_user:
            seed_user = User(
                username="Seed User",
                email="seed-user@example.com",
                role="user",
                credits=20,
            )
            session.add(seed_user)
            await session.flush()

        sample_thread = ChatThread(
            session_id="seed-session-001",
            user_id=seed_user.id,
            title="Roadmap Summary",
            message_count=2,
            last_message_preview="Sure. The roadmap focuses on improved agent orchestration...",
        )

        sample_messages = [
            ChatMessage(
                thread=sample_thread,
                role="user",
                content="Hello! Can you summarize the latest product roadmap?",
                total_tokens=10,
            ),
            ChatMessage(
                thread=sample_thread,
                role="assistant",
                content="Sure. The roadmap focuses on improved agent orchestration, better error handling, and PostgreSQL persistence for chat history.",
                total_tokens=25,
                model="gemini-2.5-flash",
                routed_to="orchestrator",
            ),
        ]

        sample_feedback = Feedback(
            feedback_id="seed-feedback-001",
            session_id=sample_thread.session_id,
            user_id=seed_user.id,
            message_id=None,
            rating=5,
            comment="The response was helpful and well-structured.",
        )

        session.add(sample_thread)
        session.add_all(sample_messages)
        session.add(sample_feedback)
        await session.commit()


async def init_db():
    """Create all database tables, ensure schema migrations, and run seeds."""
    async with engine.begin() as conn:
        if "postgresql" in database_url or "postgres" in database_url:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
        await conn.run_sync(Base.metadata.create_all)
        try:
            if "postgresql" in database_url or "postgres" in database_url:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_created ON chat_messages(thread_id, created_at ASC);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_threads_user_created ON chat_threads(user_id, created_at DESC);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created ON credit_transactions(user_id, created_at DESC);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_documents_user_created ON user_documents(user_id, created_at DESC);"))
        except Exception as e:
            logger.debug("Schema migration/index creation skipped: %s", e)
    await seed_db()
