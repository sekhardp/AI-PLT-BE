from fastapi import APIRouter
from app.api.health import health_router
from app.api.v1.routes import router as v1_router

root_router = APIRouter()

# Register health endpoints at both /health and /api/health for convenience and backward compatibility
root_router.include_router(health_router, tags=["Health"])
root_router.include_router(health_router, prefix="/api", tags=["Health"])

# Register V1 endpoints under /api/v1 prefix
root_router.include_router(v1_router, prefix="/api/v1")