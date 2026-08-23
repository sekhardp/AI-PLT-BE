import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import root_router
from app.core.settings import app_settings
from app.db.session import init_db

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure system-wide logging level."""
    logging_level = getattr(logging, app_settings.logging_settings.LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("uvicorn").setLevel(logging_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown lifecycles of the application.
    """
    logger.info("Starting up and running migrations/seeding...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)

    yield

    logger.info("Shutting down the application...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title=app_settings.NAME,
        description=app_settings.DESCRIPTION,
        version=app_settings.VERSION,
        lifespan=lifespan
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include the root router
    app.include_router(root_router)

    return app


def bootstrap() -> FastAPI:
    """
    Bootstrap the FastAPI application.
    """
    configure_logging()
    logger.info("Bootstrapping the FastAPI application...")

    app = create_app()

    logger.info("FastAPI application bootstrapped successfully.")
    return app
