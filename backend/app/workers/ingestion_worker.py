"""Asynchronous ingestion pipeline worker.

Executes document text extraction, cleaning, chunking, embedding generation,
and database storage in a background task context.
"""

import logging
import time
import uuid

from sqlalchemy import select, text, update

from app.chunkers.semantic_chunker import SemanticChunker
from app.cleaners.text_cleaners import TextCleaner
from app.extractors.metadata_extractor import DocumentUnderstandingEngine
from app.database.models import DocumentVersion, Document
from app.database import session as db_session
from app.embeddings.embedding_service import EmbeddingService
from app.extractors.document_extractors import (
    DOCXExtractor,
    MarkdownExtractor,
    PDFExtractor,
    TXTExtractor,
)
from app.repositories.document_repository import DocumentRepository
from app.storage.storage_service import DocumentStorageService

logger = logging.getLogger("app")


class IngestionWorker:
    """Orchestrates asynchronous document ingestion lifecycle stages."""

    @classmethod
    async def process_document(cls, version_id: uuid.UUID, job_id: uuid.UUID) -> None:
        """Run the ingestion pipeline in the background.

        Updates database state and measures timings for each phase.
        """
        logger.info(f"Starting background ingestion for version={version_id}, job={job_id}")
        start_total = time.time()

        # Ingestion metrics
        metrics = {
            "validation_time_ms": 0,
            "extraction_time_ms": 0,
            "cleaning_time_ms": 0,
            "understanding_time_ms": 0,
            "chunking_time_ms": 0,
            "embedding_time_ms": 0,
            "database_time_ms": 0,
            "total_processing_time_ms": 0,
        }

        db_session.get_engine()
        async with db_session.async_session() as session:
            try:
                # 1. Validation & Loading
                logger.info("Worker started: validation phase")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="validation", progress=5
                )
                await session.commit()

                # Get version metadata
                stmt = select(DocumentVersion).where(DocumentVersion.id == version_id)
                res = await session.execute(stmt)
                version = res.scalar_one_or_none()
                if not version:
                    raise ValueError(f"Document version '{version_id}' not found.")

                # Fetch raw file from storage service
                file_bytes = DocumentStorageService.load_document(version.file_path)
                metrics["validation_time_ms"] = int((time.time() - start_phase) * 1000)

                # 2. Text Extraction
                logger.info("Worker: extraction phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="extraction", progress=20
                )
                await session.commit()

                file_ext = version.file_path.split(".")[-1].lower()
                filename = version.file_path.split("/")[-1].split("\\")[-1]

                if file_ext == "pdf":
                    extract_res = PDFExtractor.extract(file_bytes, filename)
                elif file_ext == "docx":
                    extract_res = DOCXExtractor.extract(file_bytes, filename)
                elif file_ext == "txt":
                    extract_res = TXTExtractor.extract(file_bytes, filename)
                elif file_ext in ("md", "markdown"):
                    extract_res = MarkdownExtractor.extract(file_bytes, filename)
                else:
                    raise ValueError(f"Unsupported file extension: {file_ext}")

                metrics["extraction_time_ms"] = int((time.time() - start_phase) * 1000)

                # 3. Cleaning
                logger.info("Worker: cleaning phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="cleaning", progress=40
                )
                await session.commit()

                cleaned_pages = TextCleaner.clean_document_text(extract_res.pages)
                metrics["cleaning_time_ms"] = int((time.time() - start_phase) * 1000)

                # 3.5 Document Understanding
                logger.info("Worker: document understanding phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="understanding", progress=50
                )
                await session.commit()
                
                # Run the deterministic metadata extraction pipeline
                document_metadata = DocumentUnderstandingEngine.extract_metadata(cleaned_pages, filename)
                
                # Update Document metadata in DB
                doc_stmt = select(Document).where(Document.id == version.document_id)
                doc_res = await session.execute(doc_stmt)
                document = doc_res.scalar_one_or_none()
                if document:
                    document.document_metadata = document_metadata
                
                metrics["understanding_time_ms"] = int((time.time() - start_phase) * 1000)

                # 4. Semantic Chunking
                logger.info("Worker: chunking phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="chunking", progress=60
                )
                await session.commit()
                
                try:
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                except ImportError:
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                
                # Initialize the production splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=150,
                    separators=["\n\n", "\n", ".", " ", ""]
                )

                # Extract raw text from PDF
                raw_text = "\n\n".join(cleaned_pages)
                
                # Force chunking through the splitter
                docs = text_splitter.create_documents([raw_text])
                
                from app.chunkers.semantic_chunker import ChunkPayload
                import hashlib
                
                chunks = []
                for idx, doc in enumerate(docs):
                    text_content = doc.page_content
                    chunk_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
                    payload = ChunkPayload(
                        chunk_index=idx,
                        page_number=1,
                        paragraph_number=idx,
                        text=text_content,
                        char_range_start=0,
                        char_range_end=len(text_content),
                        token_count=len(text_content.split()),
                        hash=chunk_hash,
                        document_id=version.document_id,
                        document_name=filename,
                        version_id=version_id,
                        document_type="document",
                        topic=document_metadata.get("title", filename)
                    )
                    chunks.append(payload)
                
                if not chunks:
                    raise ValueError("Document contains no valid semantic content after cleaning.")
                    
                metrics["chunking_time_ms"] = int((time.time() - start_phase) * 1000)

                # 5. Embeddings Generation
                logger.info("Worker: embedding phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="embedding", progress=80
                )
                await session.commit()

                # Generate embeddings with metadata context prepended
                chunk_texts_for_embedding = []
                for c in chunks:
                    metadata_prefix = f"Document: {filename} ({c.document_type})"
                    if c.topic:
                        metadata_prefix += f" | Topic: {c.topic}"
                    if c.section:
                        metadata_prefix += f" | Section: {c.section}"
                    if c.heading:
                        metadata_prefix += f" | Heading: {c.heading}"
                    metadata_prefix += f" | Type: {c.chunk_type}"
                    
                    enriched_text = f"{metadata_prefix}\n\n{c.text}"
                    chunk_texts_for_embedding.append(enriched_text)
                
                # Batch processing to prevent OOM
                embeddings = []
                batch_size = 100
                for i in range(0, len(chunk_texts_for_embedding), batch_size):
                    batch = chunk_texts_for_embedding[i:i + batch_size]
                    batch_embeddings = EmbeddingService.generate_embeddings(batch)
                    embeddings.extend(batch_embeddings)
                    
                metrics["embedding_time_ms"] = int((time.time() - start_phase) * 1000)

                # 6. Database Storage
                logger.info("Worker: database save phase started")
                start_phase = time.time()
                await DocumentRepository.update_processing_job(
                    session, job_id, status="database", progress=95
                )
                await session.commit()

                # Save chunks and their embeddings
                await DocumentRepository.create_chunks_and_embeddings(
                    session,
                    version_id=version_id,
                    chunks=chunks,
                    embeddings=embeddings,
                    embedding_model=EmbeddingService.model_name,
                )

                metrics["database_time_ms"] = int((time.time() - start_phase) * 1000)
                metrics["total_processing_time_ms"] = int((time.time() - start_total) * 1000)

                # Update DocumentVersion properties upon completion
                version.status = "ready_for_search"
                version.chunk_count = len(chunks)
                version.processing_time_ms = metrics["total_processing_time_ms"]
                version.upload_time_ms = version.upload_time_ms or 0
                version.validation_time_ms = metrics["validation_time_ms"]
                version.extraction_time_ms = metrics["extraction_time_ms"]
                version.cleaning_time_ms = metrics["cleaning_time_ms"]
                version.understanding_time_ms = metrics["understanding_time_ms"]
                version.chunking_time_ms = metrics["chunking_time_ms"]
                version.embedding_time_ms = metrics["embedding_time_ms"]
                version.database_time_ms = metrics["database_time_ms"]

                # (ANALYZE document_chunks removed to prevent database thrashing)

                # Verification: ensure chunks are actually searchable
                from sqlalchemy import func
                from app.database.models import DocumentChunk
                verify_stmt = select(func.count()).select_from(DocumentChunk).where(
                    DocumentChunk.version_id == version_id
                )
                verify_result = await session.execute(verify_stmt)
                stored_count = verify_result.scalar()
                if stored_count != len(chunks):
                    logger.warning(
                        "Verification mismatch: expected %d chunks, found %d",
                        len(chunks), stored_count,
                    )
                else:
                    logger.info(
                        "Verification passed: %d chunks stored and searchable for %s",
                        stored_count, filename,
                    )

                # Update dynamic words cache
                try:
                    import re
                    from app.utils.conversation import update_dynamic_known_words
                    chunk_words = set()
                    for c in chunks:
                        if c.text:
                            chunk_words.update(re.findall(r"\b\w+\b", c.text.lower()))
                    if chunk_words:
                        update_dynamic_known_words(chunk_words)
                except Exception as e:
                    logger.error("Failed to update dynamic known words: %s", e)

                # Invalidate indexed vocabulary cache so new documents are immediately routable
                try:
                    from app.engines.query_decision_engine import _indexed_vocab_cache
                    import app.engines.query_decision_engine as qde_module
                    qde_module._indexed_vocab_cache = None
                    qde_module._indexed_vocab_timestamp = 0.0
                except Exception:
                    pass

                # Finalize job
                await DocumentRepository.update_processing_job(
                    session, job_id, status="completed", progress=100
                )
                await session.commit()
                logger.info("Worker: completed successfully")

            except Exception as e:
                logger.error(f"Ingestion worker failed on version={version_id}: {e}", exc_info=True)
                metrics["total_processing_time_ms"] = int((time.time() - start_total) * 1000)

                # Rollback changes within session
                await session.rollback()

                # Mark version and job as FAILED
                try:
                    # Fetch fresh version to edit status safely
                    v_stmt = update(DocumentVersion).where(DocumentVersion.id == version_id).values(
                        status="failed",
                        processing_time_ms=metrics["total_processing_time_ms"]
                    )
                    await session.execute(v_stmt)

                    await DocumentRepository.update_processing_job(
                        session,
                        job_id,
                        status="failed",
                        progress=100,
                        error_message=str(e),
                    )
                    await session.commit()
                except Exception as db_err:
                    logger.critical(f"Failed to record processing failure status to database: {db_err}")
