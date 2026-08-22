import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, status

health_router = APIRouter()

@health_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Returns the health status of the application.",
    response_model=dict[str, Any],
)
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint to verify the application's health status.

    Returns:
        dict[str, Any]: A dictionary containing the health status and timestamp.
    """
    logging.info("Health check requested.")
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }   