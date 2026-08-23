import os
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile

from app.api.v1.schemas.upload import UploadResponse
from app.core.settings import app_settings


class UploadService:
    """
    Service to handle local file upload storage, path creations, and size validation checks.
    """

    def __init__(self, upload_dir: str | None = None, max_size_mb: int | None = None):
        self.upload_dir = upload_dir or app_settings.upload_settings.DIR
        self.max_size_mb = max_size_mb or app_settings.upload_settings.MAX_SIZE_MB

    async def save_file(self, file: UploadFile) -> UploadResponse:
        """Read, validate, and write upload file to server's uploads storage."""
        content = await file.read()
        if len(content) > self.max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {self.max_size_mb}MB limit"
            )

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename or "")[1]
        saved_name = f"{file_id}{ext}"
        save_path = os.path.join(self.upload_dir, saved_name)

        os.makedirs(self.upload_dir, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(content)

        return UploadResponse(
            file_id=file_id,
            filename=file.filename or saved_name,
            size_bytes=len(content),
            content_type=file.content_type or "application/octet-stream",
            uploaded_at=datetime.now(UTC).isoformat(),
            path=save_path,
        )


def get_upload_service() -> UploadService:
    """Dependency injection helper for UploadService."""
    return UploadService()
