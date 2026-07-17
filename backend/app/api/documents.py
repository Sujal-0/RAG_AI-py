"""API router defining REST endpoints for document ingestion and semantic search.

Exposes endpoints for document upload, listing, details, deletion, job status,
and pgvector semantic searches.
"""

import hashlib
import time
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.database.session import get_db_session
from app.embeddings.embedding_service import EmbeddingService
from app.repositories.document_repository import DocumentRepository
from app.storage.storage_service import DocumentStorageService
from app.workers.ingestion_worker import IngestionWorker

import logging

logger = logging.getLogger("app")

router = APIRouter(prefix="/documents", tags=["Documents Ingestion"])


# Pydantic schemas for request/response models
class SearchRequest(BaseModel):
    """Validation schema for semantic query search."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(5, ge=1, le=50)


class SearchResponseItem(BaseModel):
    """Validation schema for a single semantic search chunk hit."""
    score: float
    chunk_id: str
    document_id: str
    version_number: int
    filename: str
    page_number: int
    heading: str | None
    section: str | None
    text: str
    token_count: int


class IngestionQueueResponse(BaseModel):
    """Validation schema returned upon successful document upload accepting."""
    success: bool = True
    message: str
    documentId: str
    versionId: str
    jobId: str


# Helper for extension/mime validation
SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "md", "markdown"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "application/octet-stream", # Some markdown/text files present as octet streams
}


@router.post(
    "/upload",
    response_model=IngestionQueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Upload a document file to start the ingestion pipeline asynchronously.

    Checks extension, MIME type, size, checksum duplicates, and creates database
    version controls before offloading text parsing to the background worker.
    """
    start_upload = time.time()
    filename = file.filename or "unknown"
    logger.info("Upload endpoint entered: filename=%s", filename)

    # 1. Validate File Extension
    file_ext = filename.split(".")[-1].lower() if "." in filename else ""
    if file_ext not in SUPPORTED_EXTENSIONS:
        logger.warning("Validation failed: unsupported extension .%s", file_ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '.{file_ext}'. Supported types: {SUPPORTED_EXTENSIONS}",
        )

    # 2. Validate MIME Type
    mime_type = file.content_type
    if mime_type and mime_type not in SUPPORTED_MIME_TYPES:
        logger.warning("Validation failed: unsupported MIME type %s", mime_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{mime_type}'.",
        )

    # 3. Read bytes & Validate size
    file_bytes = await file.read()
    max_bytes = settings.upload.max_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        logger.warning("Validation failed: file exceeds max size limit")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.upload.max_file_size_mb}MB.",
        )

    # 4. Generate Checksum for Duplicate Detection
    checksum = hashlib.sha256(file_bytes).hexdigest()
    logger.info("Validation finished: filename=%s, checksum=%s", filename, checksum)
    
    duplicate_version = await DocumentRepository.get_version_by_checksum(db, checksum)
    if duplicate_version:
        logger.warning("Upload rejected: duplicate file checksum detected")
        await DocumentRepository.create_upload_log(
            db, filename, len(file_bytes), checksum, status="duplicate"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate document detected. This exact file checksum has already been ingested.",
        )

    # 5. Version Check
    existing_doc = await DocumentRepository.get_document_by_filename(db, filename)
    if existing_doc:
        version_number = existing_doc.latest_version + 1
        existing_doc.latest_version = version_number
        doc = existing_doc
    else:
        version_number = 1
        doc = await DocumentRepository.create_document(db, filename, file_ext)
    logger.info("Document entry fetched/created: id=%s, version=%s", doc.id, version_number)

    # 6. Save File using the Storage Service
    try:
        file_path = DocumentStorageService.save_document(filename, version_number, file_bytes)
        logger.info("File saved to storage: path=%s", file_path)
    except Exception as e:
        logger.error("Storage service persist failed: %s", e)
        await DocumentRepository.create_upload_log(
            db, filename, len(file_bytes), checksum, status="storage_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist file in storage service: {e}",
        )

    # 7. Create database records (version & processing job)
    upload_time_ms = int((time.time() - start_upload) * 1000)
    version = await DocumentRepository.create_document_version(
        db,
        document_id=doc.id,
        version_number=version_number,
        checksum=checksum,
        file_path=file_path,
        file_size=len(file_bytes),
        embedding_model=EmbeddingService.model_name,
    )

    # Store upload metrics time
    version.upload_time_ms = upload_time_ms

    job = await DocumentRepository.create_processing_job(db, version_id=version.id)
    await DocumentRepository.create_upload_log(
        db, filename, len(file_bytes), checksum, status="processing"
    )
    await db.commit()
    logger.info("Database records created for version=%s, job=%s", version.id, job.id)

    # 8. Dispatch Background processing worker
    background_tasks.add_task(IngestionWorker.process_document, version.id, job.id)
    logger.info("Background task scheduled for job=%s. Returning HTTP 202", job.id)

    return {
        "success": True,
        "message": "Document accepted and queued for background indexing.",
        "documentId": str(doc.id),
        "versionId": str(version.id),
        "jobId": str(job.id),
    }


@router.get("", response_model=list[dict[str, Any]])
async def list_documents(db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    """Retrieve lists of all documents with active status profiles."""
    return await DocumentRepository.get_documents_list(db)


@router.get("/{document_id}", response_model=dict[str, Any])
async def get_document_details(
    document_id: str, db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Fetch complete metadata details and chunk mappings for a specific document."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format."
        )

    details = await DocumentRepository.get_document_details(db, doc_uuid)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    return details


@router.delete("/{document_id}")
async def delete_document(
    document_id: str, db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Delete a document, cascade deleting physical files and all database chunk vectors."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format."
        )

    success = await DocumentRepository.delete_document(db, doc_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    await db.commit()
    return {"success": True, "message": "Document and all associated versions successfully deleted."}


@router.get("/jobs/{job_id}", response_model=dict[str, Any])
async def get_job_status(
    job_id: str, db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Track progress and telemetry timings of an active background processing job."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format."
        )

    job_status = await DocumentRepository.get_job_status(db, job_uuid)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        )
    return job_status


@router.post("/search", response_model=list[SearchResponseItem])
async def semantic_search(
    body: SearchRequest, db: AsyncSession = Depends(get_db_session)
) -> list[dict[str, Any]]:
    """Performs cosine vector search on stored document chunks and returns closest matches."""
    try:
        # Load embedding model and encode search string
        query_embedding = EmbeddingService.generate_embedding(body.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding model execution failed: {e}",
        )

    # Perform pgvector cosine distance search
    results = await DocumentRepository.vector_search(db, query_embedding, limit=body.limit)
    return results
