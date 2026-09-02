import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.document_service import document_service

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/documents", tags=["Documents & Knowledge"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form("default_user"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Upload and index a document into Cloud SQL pgvector.
    Enforces quota: max 5 documents, max 100MB cumulative per user.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        doc = await document_service.ingest_document(
            user_id=user_id,
            filename=file.filename,
            content=content,
            mime_type=file.content_type or "",
            db=db,
        )
        return {
            "status": "ok",
            "document": {
                "id": str(doc.id),
                "filename": doc.filename,
                "file_size_bytes": doc.file_size_bytes,
                "status": doc.status,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Document ingestion error: %s", e)
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {e!s}")


@router.get("")
async def list_documents(
    user_id: str = "default_user",
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve all uploaded documents and current storage quota for the user."""
    try:
        return await document_service.list_documents(user_id=user_id, db=db)
    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = "default_user",
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a document and all of its vector embeddings."""
    try:
        deleted = await document_service.delete_document(doc_id=document_id, user_id=user_id, db=db)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "ok", "deleted_id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

