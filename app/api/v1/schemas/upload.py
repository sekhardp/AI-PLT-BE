from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    uploaded_at: str
    path: str


__all__ = ["UploadResponse"]
