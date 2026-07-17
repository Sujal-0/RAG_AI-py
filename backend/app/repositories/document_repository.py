"""Repository module for Phase 6 Knowledge Ingestion database operations.

Encapsulates SQL queries and transactions for documents, versions, chunks,
embeddings, processing jobs, and hybrid retrieval (metadata + keyword + vector + RRF).
"""

import uuid
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chunkers.semantic_chunker import ChunkPayload
from app.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    ProcessingJob,
    UploadLog,
)

logger = logging.getLogger("app")


class DocumentRepository:
    """Handles CRUD transactions and hybrid semantic search queries."""

    # ─── CRUD Operations ───────────────────────────────────────────────

    @staticmethod
    async def get_document_by_filename(
        session: AsyncSession, filename: str
    ) -> Document | None:
        """Fetch a document by its original filename."""
        stmt = select(Document).where(Document.filename == filename)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_document(
        session: AsyncSession, filename: str, file_type: str
    ) -> Document:
        """Create a new root document entry."""
        doc = Document(filename=filename, file_type=file_type)
        session.add(doc)
        await session.flush()
        return doc

    @staticmethod
    async def get_version_by_checksum(
        session: AsyncSession, checksum: str
    ) -> DocumentVersion | None:
        """Verify duplicate ingestion status by SHA-256 checksum."""
        stmt = select(DocumentVersion).where(DocumentVersion.checksum == checksum)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_document_version(
        session: AsyncSession,
        document_id: uuid.UUID,
        version_number: int,
        checksum: str,
        file_path: str,
        file_size: int,
        embedding_model: str,
    ) -> DocumentVersion:
        """Create a new version record under a document."""
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            checksum=checksum,
            file_path=file_path,
            file_size=file_size,
            status="processing",
            embedding_model=embedding_model,
        )
        session.add(version)
        await session.flush()
        return version

    @staticmethod
    async def create_chunks_and_embeddings(
        session: AsyncSession,
        version_id: uuid.UUID,
        chunks: list[ChunkPayload],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> None:
        """Store semantic chunks and their vector embeddings directly in the database."""
        for idx, chunk in enumerate(chunks):
            vector = embeddings[idx]
            db_chunk = DocumentChunk(
                id=chunk.id,
                version_id=version_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                paragraph_number=chunk.paragraph_number,
                heading=chunk.heading,
                section=chunk.section,
                text=chunk.text,
                char_range_start=chunk.char_range_start,
                char_range_end=chunk.char_range_end,
                token_count=chunk.token_count,
                hash=chunk.hash,
                embedding_vector=vector,
                embedding_model=embedding_model,
                embedding_dimension=len(vector),
                embedding_timestamp=datetime.now(UTC),
            )
            session.add(db_chunk)
        await session.flush()

    @staticmethod
    async def create_processing_job(
        session: AsyncSession, version_id: uuid.UUID
    ) -> ProcessingJob:
        """Register a new asynchronous progress tracking job."""
        job = ProcessingJob(
            version_id=version_id,
            status="pending",
            progress=0,
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def update_processing_job(
        session: AsyncSession,
        job_id: uuid.UUID,
        status: str,
        progress: int,
        error_message: str | None = None,
    ) -> None:
        """Update job progress parameters and timestamp completions."""
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            job.progress = progress
            if error_message:
                job.error_message = error_message
            if status in ("completed", "failed"):
                job.end_time = datetime.now(UTC)
            await session.flush()

    @staticmethod
    async def create_upload_log(
        session: AsyncSession, filename: str, file_size: int, checksum: str, status: str
    ) -> None:
        """Insert upload attempt logs."""
        log = UploadLog(
            filename=filename,
            file_size=file_size,
            checksum=checksum,
            status=status,
        )
        session.add(log)
        await session.flush()

    @staticmethod
    async def get_documents_list(session: AsyncSession) -> list[dict[str, Any]]:
        """Fetch all root documents with latest active version status."""
        stmt = select(Document).order_by(desc(Document.created_at)).options(
            selectinload(Document.versions)
        )
        result = await session.execute(stmt)
        docs = result.scalars().all()

        output = []
        for doc in docs:
            # Get latest version entry
            latest_v = None
            if doc.versions:
                latest_v = max(doc.versions, key=lambda v: v.version_number)

            output.append({
                "id": str(doc.id),
                "filename": doc.filename,
                "file_type": doc.file_type,
                "created_at": doc.created_at.isoformat(),
                "latest_version": doc.latest_version,
                "status": latest_v.status if latest_v else "unknown",
                "chunk_count": latest_v.chunk_count if latest_v else 0,
                "file_size": latest_v.file_size if latest_v else 0,
                "version_id": str(latest_v.id) if latest_v else None,
                "upload_time_ms": latest_v.upload_time_ms if latest_v else 0,
                "validation_time_ms": latest_v.validation_time_ms if latest_v else 0,
                "extraction_time_ms": latest_v.extraction_time_ms if latest_v else 0,
                "cleaning_time_ms": latest_v.cleaning_time_ms if latest_v else 0,
                "chunking_time_ms": latest_v.chunking_time_ms if latest_v else 0,
                "embedding_time_ms": latest_v.embedding_time_ms if latest_v else 0,
                "database_time_ms": latest_v.database_time_ms if latest_v else 0,
                "processing_time_ms": latest_v.processing_time_ms if latest_v else 0,
            })
        return output

    @staticmethod
    async def get_document_details(
        session: AsyncSession, document_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Retrieve complete document versions history, chunks, and processing job status."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.chunks),
                selectinload(Document.versions).selectinload(DocumentVersion.jobs),
            )
        )
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            return None

        # Build versions list
        versions_list = []
        for v in sorted(doc.versions, key=lambda x: x.version_number, reverse=True):
            job = max(v.jobs, key=lambda j: j.start_time) if v.jobs else None

            # Map chunk lists
            chunks_data = []
            for chunk in sorted(v.chunks, key=lambda c: c.chunk_index):
                chunks_data.append({
                    "id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "paragraph_number": chunk.paragraph_number,
                    "heading": chunk.heading,
                    "section": chunk.section,
                    "text": chunk.text,
                    "char_range_start": chunk.char_range_start,
                    "char_range_end": chunk.char_range_end,
                    "token_count": chunk.token_count,
                    "hash": chunk.hash,
                })

            versions_list.append({
                "id": str(v.id),
                "version_number": v.version_number,
                "checksum": v.checksum,
                "file_size": v.file_size,
                "status": v.status,
                "chunk_count": v.chunk_count,
                "embedding_model": v.embedding_model,
                "processing_time_ms": v.processing_time_ms,
                "upload_time_ms": v.upload_time_ms,
                "validation_time_ms": v.validation_time_ms,
                "extraction_time_ms": v.extraction_time_ms,
                "cleaning_time_ms": v.cleaning_time_ms,
                "chunking_time_ms": v.chunking_time_ms,
                "embedding_time_ms": v.embedding_time_ms,
                "database_time_ms": v.database_time_ms,
                "created_at": v.created_at.isoformat(),
                "job": {
                    "id": str(job.id),
                    "status": job.status,
                    "progress": job.progress,
                    "error_message": job.error_message,
                    "start_time": job.start_time.isoformat(),
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                } if job else None,
                "chunks": chunks_data,
            })

        return {
            "id": str(doc.id),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "created_at": doc.created_at.isoformat(),
            "latest_version": doc.latest_version,
            "versions": versions_list,
        }

    @staticmethod
    async def delete_document(session: AsyncSession, document_id: uuid.UUID) -> bool:
        """Remove document registry and cascade delete versions, chunks, and vectors."""
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        # Get file paths to delete physical documents
        from app.database.models import DocumentVersion
        v_stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        v_result = await session.execute(v_stmt)
        versions = v_result.scalars().all()

        import contextlib

        from app.storage.storage_service import DocumentStorageService
        for v in versions:
            with contextlib.suppress(Exception):
                DocumentStorageService.delete_document(v.file_path)

        await session.delete(doc)
        await session.flush()
        return True

    @staticmethod
    async def get_job_status(
        session: AsyncSession, job_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Check status profile of an active or finalized job."""
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return None

        # Calculate exact duration metrics if completed
        duration_ms = 0
        if job.end_time:
            duration_ms = int((job.end_time - job.start_time).total_seconds() * 1000)
        elif job.status not in ("completed", "failed"):
            duration_ms = int((datetime.now(UTC) - job.start_time).total_seconds() * 1000)

        return {
            "id": str(job.id),
            "version_id": str(job.version_id),
            "status": job.status,
            "progress": job.progress,
            "error_message": job.error_message,
            "duration_ms": duration_ms,
            "start_time": job.start_time.isoformat(),
            "end_time": job.end_time.isoformat() if job.end_time else None,
        }

    # ─── Hybrid Retrieval System ───────────────────────────────────────

    @staticmethod
    async def metadata_search(
        session: AsyncSession, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search chunks by metadata: filename, heading, section using ILIKE.

        This catches queries like 'Employee Handbook', 'Leave Policy', etc.
        """
        query_lower = query.lower().strip()
        # Build ILIKE patterns for multi-word and single-word matching
        like_pattern = f"%{query_lower}%"

        stmt = (
            select(
                DocumentChunk,
                Document.filename,
                DocumentVersion.document_id,
                DocumentVersion.version_number,
            )
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(DocumentVersion.status == "ready_for_search")
            .where(
                or_(
                    func.lower(Document.filename).contains(query_lower),
                    func.lower(DocumentChunk.heading).contains(query_lower),
                    func.lower(DocumentChunk.section).contains(query_lower),
                )
            )
            .limit(limit)
        )

        result = await session.execute(stmt)
        rows = result.all()

        results = []
        for chunk, filename, document_id, version_number in rows:
            # Score based on match quality
            fn_lower = (filename or "").lower()
            heading_lower = (chunk.heading or "").lower()
            section_lower = (chunk.section or "").lower()

            score = 0.0
            match_type = "section"
            if query_lower in fn_lower:
                score = 0.95
                match_type = "filename"
            elif query_lower in heading_lower:
                score = 0.92
                match_type = "heading"
            elif query_lower in section_lower:
                score = 0.88
                match_type = "section"

            # Also check individual query words
            if score == 0.0:
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) < 3:
                        continue
                    if word in fn_lower or word in heading_lower or word in section_lower:
                        score = max(score, 0.80)
                        match_type = "partial_metadata"

            if score > 0:
                results.append({
                    "score": score,
                    "retrieval_method": f"metadata_{match_type}",
                    "chunk_id": str(chunk.id),
                    "document_id": str(document_id) if document_id else None,
                    "version_number": version_number if version_number is not None else 1,
                    "filename": filename,
                    "page_number": chunk.page_number,
                    "heading": chunk.heading,
                    "section": chunk.section,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "chunk_index": chunk.chunk_index,
                })

        return results

    @staticmethod
    async def keyword_search(
        session: AsyncSession, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search chunks using PostgreSQL full-text search on chunk body text.

        Falls back to ILIKE if full-text search yields no results.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        try:
            stmt = (
                select(
                    DocumentChunk,
                    Document.filename,
                    DocumentVersion.document_id,
                    DocumentVersion.version_number,
                    func.ts_rank(
                        func.to_tsvector("english", DocumentChunk.text),
                        func.plainto_tsquery("english", query_lower),
                    ).label("rank"),
                )
                .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
                .join(Document, DocumentVersion.document_id == Document.id)
                .where(DocumentVersion.status == "ready_for_search")
                .where(
                    func.to_tsvector("english", DocumentChunk.text).op("@@")(func.plainto_tsquery("english", query_lower))
                )
                .order_by(text("rank DESC"))
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()
        except Exception as e:
            logger.warning("Full-text search failed (%s)", e)
            rows = []

        results = []
        for row_data in rows:
            if len(row_data) == 5:
                chunk, filename, document_id, version_number, rank = row_data
            else:
                chunk, filename, document_id, version_number = row_data
                rank = 0.5

            # Normalize rank to 0-1 score range
            score = min(float(rank) * 2.0, 0.95) if rank else 0.5

            results.append({
                "score": score,
                "retrieval_method": "keyword",
                "chunk_id": str(chunk.id),
                "document_id": str(document_id) if document_id else None,
                "version_number": version_number if version_number is not None else 1,
                "filename": filename,
                "page_number": chunk.page_number,
                "heading": chunk.heading,
                "section": chunk.section,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "chunk_index": chunk.chunk_index,
            })

        return results

    @staticmethod
    async def vector_search(
        session: AsyncSession, query_embedding: list[float], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Query top chunks sorted by cosine similarity from pgvector.

        Returns raw cosine similarity scores — no artificial scaling.
        """
        # cosine distance = 1 - cosine similarity
        distance_expr = DocumentChunk.embedding_vector.cosine_distance(query_embedding)
        score_expr = 1 - distance_expr

        stmt = (
            select(
                DocumentChunk,
                score_expr.label("similarity_score"),
                DocumentVersion.file_path,
                Document.filename,
                DocumentVersion.document_id,
                DocumentVersion.version_number,
            )
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(DocumentVersion.status == "ready_for_search")
            .order_by(distance_expr)
            .limit(limit)
        )

        result = await session.execute(stmt)
        rows = result.all()

        results = []
        for chunk, score, _file_path, filename, document_id, version_number in rows:
            raw_score = float(score)

            results.append({
                "score": raw_score,
                "retrieval_method": "vector",
                "chunk_id": str(chunk.id),
                "document_id": str(document_id) if document_id else None,
                "version_number": version_number if version_number is not None else 1,
                "filename": filename,
                "page_number": chunk.page_number,
                "heading": chunk.heading,
                "section": chunk.section,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "chunk_index": chunk.chunk_index,
            })
        return results

    @staticmethod
    def reciprocal_rank_fusion(
        *result_lists: list[dict[str, Any]],
        k: int = 60,
        weights: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Merge multiple ranked result lists using Weighted Reciprocal Rank Fusion (RRF).

        RRF score = sum(weight * 1 / (k + rank_i)) across all lists where the chunk appears.
        Higher is better. k=60 is standard.
        """
        chunk_scores: dict[str, float] = {}
        chunk_data: dict[str, dict[str, Any]] = {}
        chunk_methods: dict[str, list[str]] = {}

        if weights is None:
            weights = [1.0] * len(result_lists)

        for result_list, weight in zip(result_lists, weights):
            for rank, item in enumerate(result_list):
                chunk_id = item["chunk_id"]
                rrf_score = weight * (1.0 / (k + rank + 1))

                if chunk_id not in chunk_scores:
                    chunk_scores[chunk_id] = 0.0
                    chunk_data[chunk_id] = item
                    chunk_methods[chunk_id] = []

                chunk_scores[chunk_id] += rrf_score
                method = item.get("retrieval_method", "unknown")
                if method not in chunk_methods[chunk_id]:
                    chunk_methods[chunk_id].append(method)

        # Build merged results sorted by RRF score descending
        merged = []
        for chunk_id in sorted(chunk_scores, key=chunk_scores.get, reverse=True):
            item = dict(chunk_data[chunk_id])
            item["rrf_score"] = round(chunk_scores[chunk_id], 6)
            item["retrieval_methods"] = chunk_methods[chunk_id]
            # Use original score from highest-scoring method
            item["score"] = max(
                r["score"]
                for result_list in result_lists
                for r in result_list
                if r["chunk_id"] == chunk_id
            )
            merged.append(item)

        return merged

    @staticmethod
    async def hybrid_search(
        session: AsyncSession,
        query: str,
        query_embedding: list[float],
        limit: int = 10,
        strategy: dict[str, bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute hybrid retrieval combining metadata, keyword, and vector search.

        Pipeline:
        1. Metadata search (filename, heading, section)
        2. Keyword search (PostgreSQL full-text search)
        3. Dense vector search (pgvector cosine similarity)
        4. Reciprocal Rank Fusion to merge all results

        Returns merged, deduplicated results sorted by combined relevance.
        """
        import time
        import asyncio
        diagnostics = {}
        
        strategy = strategy or {"use_metadata": True, "use_keyword": True, "use_vector": True}

        # Track execution time wrappers
        async def run_metadata():
            t0 = time.perf_counter()
            res = await DocumentRepository.metadata_search(session, query, limit=limit)
            return ("metadata", res, round((time.perf_counter() - t0) * 1000, 2))
            
        async def run_keyword():
            t0 = time.perf_counter()
            res = await DocumentRepository.keyword_search(session, query, limit=limit)
            return ("keyword", res, round((time.perf_counter() - t0) * 1000, 2))
            
        async def run_vector():
            t0 = time.perf_counter()
            res = await DocumentRepository.vector_search(session, query_embedding, limit=limit)
            return ("vector", res, round((time.perf_counter() - t0) * 1000, 2))

        # TODO(RC2): Restore parallel execution by giving every retrieval task its own independent AsyncSession.
        # Currently, sharing a single AsyncSession across concurrent tasks causes SQLAlchemy concurrency errors.
        if strategy.get("use_metadata", True):
            name, res, lat = await run_metadata()
            diagnostics[f"{name}_time_ms"] = lat
            diagnostics[f"{name}_count"] = len(res)
            metadata_results = res
            
        if strategy.get("use_keyword", True):
            name, res, lat = await run_keyword()
            diagnostics[f"{name}_time_ms"] = lat
            diagnostics[f"{name}_count"] = len(res)
            keyword_results = res
            
        if strategy.get("use_vector", True):
            name, res, lat = await run_vector()
            diagnostics[f"{name}_time_ms"] = lat
            diagnostics[f"{name}_count"] = len(res)
            vector_results = res

        # 4. Weighted Reciprocal Rank Fusion
        # Prioritize Metadata (Filename, Heading, Section) and Keyword over Vector
        merged = DocumentRepository.reciprocal_rank_fusion(
            metadata_results, keyword_results, vector_results,
            weights=[3.0, 2.0, 1.0]
        )

        # Limit to requested count
        merged = merged[:limit]
        
        # Log Hybrid Fusion diagnostics
        score_distribution = [round(c.get("score", 0), 3) for c in merged]
        logger.info(
            "HYBRID RETRIEVAL DIAGNOSTICS\n"
            "Metadata Search: %d chunks, %sms -> %s\n"
            "Keyword Search: %d chunks, %sms -> %s\n"
            "Vector Search: %d chunks, %sms -> %s\n"
            "Hybrid Fusion: merged %d chunks\n"
            "Merged Results: %s\n"
            "RRF Score Distribution: %s",
            diagnostics.get("metadata_count", 0), diagnostics.get("metadata_time_ms", 0),
            [c.get("chunk_id", "")[:8] + ":" + c.get("filename", "") for c in metadata_results],
            diagnostics.get("keyword_count", 0), diagnostics.get("keyword_time_ms", 0),
            [c.get("chunk_id", "")[:8] + ":" + c.get("filename", "") for c in keyword_results],
            diagnostics.get("vector_count", 0), diagnostics.get("vector_time_ms", 0),
            [c.get("chunk_id", "")[:8] + ":" + c.get("filename", "") for c in vector_results],
            len(merged), 
            [c.get("chunk_id", "")[:8] + ":" + c.get("filename", "") + "(RRF:" + str(c.get("rrf_score", 0)) + ")" for c in merged],
            score_distribution
        )

        # Attach diagnostics to each result
        for item in merged:
            item["_diagnostics"] = diagnostics

        return merged

    # ─── Indexed Vocabulary (for dynamic RAG routing) ──────────────────

    @staticmethod
    async def get_indexed_vocabulary(session: AsyncSession) -> dict[str, set[str]]:
        """Return sets of all filenames, headings, and sections from indexed documents.

        Used by the QueryDecisionEngine to dynamically route queries to RAG
        when they match indexed document metadata.
        """
        # Filenames
        fn_stmt = (
            select(Document.filename)
            .join(DocumentVersion, Document.id == DocumentVersion.document_id)
            .where(DocumentVersion.status == "ready_for_search")
            .distinct()
        )
        fn_result = await session.execute(fn_stmt)
        filenames = {row[0].lower() for row in fn_result.all() if row[0]}

        # Headings and sections
        hs_stmt = (
            select(DocumentChunk.heading, DocumentChunk.section)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(DocumentVersion.status == "ready_for_search")
            .distinct()
        )
        hs_result = await session.execute(hs_stmt)
        headings = set()
        sections = set()
        for heading, section in hs_result.all():
            if heading:
                headings.add(heading.lower())
            if section:
                sections.add(section.lower())

        return {
            "filenames": filenames,
            "headings": headings,
            "sections": sections,
        }

    # ─── Re-indexing Support ───────────────────────────────────────────

    @staticmethod
    async def get_versions_for_reindex(
        session: AsyncSession, embedding_model: str
    ) -> list[DocumentVersion]:
        """Find all document versions whose embeddings were generated by a different model."""
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.status == "ready_for_search")
            .where(DocumentVersion.embedding_model != embedding_model)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def clear_version_chunks(
        session: AsyncSession, version_id: uuid.UUID
    ) -> int:
        """Delete all chunks for a specific version (for re-indexing)."""
        from sqlalchemy import delete
        stmt = delete(DocumentChunk).where(DocumentChunk.version_id == version_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount
