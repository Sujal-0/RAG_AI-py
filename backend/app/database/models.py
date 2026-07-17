"""Database ORM models for the Knowledge Ingestion Platform.

Defines the tables for documents, versions, chunks, jobs, and upload logs.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    text
)
from sqlalchemy.dialects.postgresql import JSONB
from app.core.settings import settings
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class Document(Base):
    """Main Documents registry table."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    latest_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    """Document Versions registry supporting document version control."""

    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # processing, ready_for_search, failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upload_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cleaning_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    understanding_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunking_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    database_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="versions")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="version", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="version", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Document chunks table containing both chunk text and pgvector embeddings."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index('ix_document_chunks_fts', text("to_tsvector('english', text)"), postgresql_using='gin'),
        Index('ix_document_chunks_metadata', "chunk_metadata", postgresql_using='gin'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_range_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_range_end: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # pgvector Embedding Columns (Merged into chunk table)
    embedding_vector: Mapped[Any] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=settings.EMBEDDING_DIMENSION, nullable=False)
    embedding_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", back_populates="chunks")


class ProcessingJob(Base):
    """Asynchronous processing jobs progress tracking table."""

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, extraction, cleaning, chunking, embedding, database, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", back_populates="jobs")


class UploadLog(Base):
    """Ingestion/Upload logs for audit and monitoring."""

    __tablename__ = "upload_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
