from fastapi import APIRouter, Depends, File, UploadFile

from app.api.v1.schemas.upload import UploadResponse
from app.services.upload_service import UploadService, get_upload_service

router = APIRouter()


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service)
):
    """Upload a document to the server for processing or RAG context injection."""
    return await upload_service.save_file(file)
