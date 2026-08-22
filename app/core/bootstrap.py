import logging

from fastapi import FastAPI
from app.api.router import root_router

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(title="AI-PLT-BE", version="1.0.0")

    # Include the root router
    app.include_router(root_router)

    return app

def bootstrap() -> FastAPI:
    """
    Bootstrap the FastAPI application.
    """
    logging.basicConfig(level=logging.INFO)
    logging.info("Bootstrapping the FastAPI application...")

    app = create_app()

    logging.info("FastAPI application bootstrapped successfully.")
    return app
