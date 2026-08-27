from fastapi import APIRouter

from .agents import router as agents_router
from .chat import router as chat_router
from .feedback import router as feedback_router
from .history import router as history_router
from .upload import router as upload_router
from .documents import router as documents_router
from .users import router as users_router

router = APIRouter()

router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(upload_router, prefix="/upload", tags=["Upload"])
router.include_router(history_router, prefix="/history", tags=["History"])
router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
router.include_router(agents_router, prefix="/agents", tags=["Agents"])
router.include_router(documents_router)

router.include_router(users_router)
