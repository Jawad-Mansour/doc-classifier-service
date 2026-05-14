"""Browser upload endpoint that feeds the background inference pipeline."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ClassificationQueuedResponse
from app.api.deps.permissions import require_permission
from app.auth.casbin import ACTION_READ, RESOURCE_PREDICTIONS
from app.auth.users import UserRead
from app.db.session import get_session
from app.services import batch_service
from app.services.ingest_service import enqueue_uploaded_document, is_supported_upload

router = APIRouter(prefix="/classify", tags=["classify"])

@router.post("", response_model=ClassificationQueuedResponse)
async def classify_document(
    file: UploadFile = File(...),
    user: UserRead = Depends(require_permission(RESOURCE_PREDICTIONS, ACTION_READ)),
    session: AsyncSession = Depends(get_session),
) -> ClassificationQueuedResponse:
    del user
    filename = file.filename or "upload"
    if not is_supported_upload(filename):
        raise HTTPException(status_code=400, detail="Supported file types: .tif, .tiff, .png, .jpg, .jpeg")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        queued = await enqueue_uploaded_document(
            session,
            batch_service=batch_service,
            filename=filename,
            file_bytes=data,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ClassificationQueuedResponse(
        status=queued["status"],
        request_id=queued["request_id"],
        job_id=queued["job_id"],
        queue_job_id=queued["queue_job_id"],
        batch_id=queued["batch_id"],
        document_id=queued["document_id"],
        blob_bucket=queued["blob_bucket"],
        blob_path=queued["blob_path"],
        original_filename=queued["original_filename"],
    )
