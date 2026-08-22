from fastapi import APIRouter
from .health import health_router

root_router = APIRouter()

root_router.include_router(health_router, prefix="/api", tags=["Health"])