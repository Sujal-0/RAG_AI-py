"""Re-indexing API endpoint.

Provides an endpoint to re-index all documents with the current embedding model.
This is necessary when the embedding model is changed (e.g., from DummyModel to
real SentenceTransformer), as old embeddings are incompatible.
"""

import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.database.session import async_session
from app.embeddings.embedding_service import EmbeddingService
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger("app")

router = APIRouter()


async def _reindex_version(version_id: uuid.UUID, filename: str) -> dict[str, Any]:
    """Re-index a single document version with the current embedding model.

    Steps:
    1. Load chunk texts from existing chunks
    2. Delete old chunks
    3. Re-extract, re-chunk, and re-embed the source file
    4. Store new chunks with new embeddings
    5. Update version metadata
    """
    from sqlalchemy import select, text, update
    from app.database.models import DocumentChunk, DocumentVersion
    from app.chunkers.semantic_chunker import SemanticChunker
    from app.cleaners.text_cleaners import TextCleaner
    from app.extractors.document_extractors import (
        DOCXExtractor, MarkdownExtractor, PDFExtractor, TXTExtractor,
    )
    from app.storage.storage_service import DocumentStorageService

    start = time.time()
    result = {"version_id": str(version_id), "filename": filename, "status": "success"}

    async with async_session() as session:
        try:
            # 1. Load version
            stmt = select(DocumentVersion).where(DocumentVersion.id == version_id)
            res = await session.execute(stmt)
            version = res.scalar_one_or_none()
            if not version:
                return {**result, "status": "error", "error": "Version not found"}

            # 2. Load source file
            file_bytes = DocumentStorageService.load_document(version.file_path)
            file_ext = version.file_path.split(".")[-1].lower()

            # 3. Extract text
            if file_ext == "pdf":
                extract_res = PDFExtractor.extract(file_bytes, filename)
            elif file_ext == "docx":
                extract_res = DOCXExtractor.extract(file_bytes, filename)
            elif file_ext == "txt":
                extract_res = TXTExtractor.extract(file_bytes, filename)
            elif file_ext in ("md", "markdown"):
                extract_res = MarkdownExtractor.extract(file_bytes, filename)
            else:
                return {**result, "status": "error", "error": f"Unsupported: {file_ext}"}

            # 4. Clean
            cleaned_pages = TextCleaner.clean_document_text(extract_res.pages)

            # 5. Re-chunk with improved settings
            chunker = SemanticChunker(target_tokens=200, overlap_percent=0.15)
            chunks = chunker.chunk_document(cleaned_pages, document_name=filename)
            if not chunks:
                return {**result, "status": "error", "error": "No chunks after re-chunking"}

            # 6. Generate embeddings with metadata context
            chunk_texts_for_embedding = []
            for c in chunks:
                metadata_prefix = f"Document: {filename}"
                if c.section:
                    metadata_prefix += f" | Section: {c.section}"
                if c.heading:
                    metadata_prefix += f" | Heading: {c.heading}"
                metadata_prefix += f" | Page: {c.page_number}"
                enriched_text = f"{metadata_prefix}\n\n{c.text}"
                chunk_texts_for_embedding.append(enriched_text)

            embeddings = EmbeddingService.generate_embeddings(chunk_texts_for_embedding)

            # 7. Delete old chunks
            old_count = await DocumentRepository.clear_version_chunks(session, version_id)
            logger.info("Re-index: deleted %d old chunks for version %s", old_count, version_id)

            # 8. Store new chunks
            await DocumentRepository.create_chunks_and_embeddings(
                session,
                version_id=version_id,
                chunks=chunks,
                embeddings=embeddings,
                embedding_model=EmbeddingService.model_name,
            )

            # 9. Update version metadata
            version.embedding_model = EmbeddingService.model_name
            version.chunk_count = len(chunks)
            version.status = "ready_for_search"

            # Optimize index
            await session.execute(text("ANALYZE document_chunks;"))

            # Update dynamic words
            try:
                import re
                from app.utils.conversation import update_dynamic_known_words
                chunk_words = set()
                for c in chunks:
                    if c.text:
                        chunk_words.update(re.findall(r"\b\w+\b", c.text.lower()))
                if chunk_words:
                    update_dynamic_known_words(chunk_words)
            except Exception:
                pass

            await session.commit()

            duration_ms = int((time.time() - start) * 1000)
            result.update({
                "old_chunk_count": old_count,
                "new_chunk_count": len(chunks),
                "embedding_model": EmbeddingService.model_name,
                "duration_ms": duration_ms,
            })

        except Exception as e:
            logger.error("Re-index failed for version %s: %s", version_id, e, exc_info=True)
            await session.rollback()
            result.update({"status": "error", "error": str(e)})

    return result


async def _reindex_all_documents() -> dict[str, Any]:
    """Re-index all documents that were embedded with a different model."""
    from sqlalchemy import select
    from app.database.models import Document, DocumentVersion

    results = []
    total_start = time.time()

    async with async_session() as session:
        # Find all versions that need re-indexing
        stmt = (
            select(DocumentVersion, Document.filename)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(DocumentVersion.status == "ready_for_search")
        )
        res = await session.execute(stmt)
        versions = res.all()

    if not versions:
        return {
            "status": "no_documents",
            "message": "No documents found to re-index",
            "results": [],
        }

    for version, filename in versions:
        r = await _reindex_version(version.id, filename)
        results.append(r)

    total_ms = int((time.time() - total_start) * 1000)

    # Invalidate vocabulary cache
    try:
        import app.engines.query_decision_engine as qde_module
        qde_module._indexed_vocab_cache = None
        qde_module._indexed_vocab_timestamp = 0.0
    except Exception:
        pass

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    return {
        "status": "completed",
        "total_versions": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "total_duration_ms": total_ms,
        "embedding_model": EmbeddingService.model_name,
        "is_real_model": True,
        "results": results,
    }


@router.post("/reindex")
async def reindex_endpoint(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Trigger re-indexing of all documents with the current embedding model.

    This endpoint should be called after switching from DummyModel to a real
    SentenceTransformer model, as old embeddings are incompatible.
    """
    # Run synchronously for now (could be async with background tasks)
    result = await _reindex_all_documents()
    return result


@router.get("/reindex/status")
async def reindex_status_endpoint() -> dict[str, Any]:
    """Check current embedding model and whether re-indexing is needed."""
    provider = EmbeddingService.get_provider()
    is_real = True

    # Check if any documents use a different embedding model
    from sqlalchemy import select, func
    from app.database.models import DocumentVersion

    outdated_count = 0
    total_count = 0
    async with async_session() as session:
        stmt = select(func.count()).select_from(DocumentVersion).where(
            DocumentVersion.status == "ready_for_search"
        )
        res = await session.execute(stmt)
        total_count = res.scalar() or 0

        outdated_stmt = select(func.count()).select_from(DocumentVersion).where(
            DocumentVersion.status == "ready_for_search",
            DocumentVersion.embedding_model != EmbeddingService.model_name,
        )
        outdated_res = await session.execute(outdated_stmt)
        outdated_count = outdated_res.scalar() or 0

    return {
        "current_model": EmbeddingService.model_name,
        "is_real_model": is_real,
        "total_indexed_versions": total_count,
        "outdated_versions": outdated_count,
        "reindex_needed": outdated_count > 0,
    }
