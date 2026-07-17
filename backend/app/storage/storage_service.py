"""Document storage service abstraction layer.

Handles file persistence operations. Currently supports local storage with an interface
that can easily pivot to cloud storage (S3/Azure Blob/GCS) in the future.
"""

import os
from pathlib import Path

from app.core.settings import settings


class DocumentStorageService:
    """Handles storage operations for raw uploaded document files."""

    @staticmethod
    def _get_storage_path() -> Path:
        """Retrieve and prepare the root upload storage path."""
        upload_path = Path(settings.upload.directory)
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    @classmethod
    def save_document(cls, filename: str, version: int, content: bytes) -> str:
        """Save a document file with version control.

        Args:
            filename: Original name of the uploaded file.
            version: Target version number of the document.
            content: Raw byte contents of the file.

        Returns:
            The absolute or relative file path where the document was saved.
        """
        storage_dir = cls._get_storage_path()
        safe_filename = Path(filename).name
        # Format versioned filename: e.g. "report_v1.pdf" or "notes_v2.md"
        stem = Path(safe_filename).stem
        suffix = Path(safe_filename).suffix
        versioned_filename = f"{stem}_v{version}{suffix}"

        file_path = storage_dir / versioned_filename

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path)

    @classmethod
    def load_document(cls, file_path: str) -> bytes:
        """Load document byte contents from storage.

        Args:
            file_path: Stored document path.

        Returns:
            The raw file byte content.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Stored file not found: {file_path}")

        with open(p, "rb") as f:
            return f.read()

    @classmethod
    def delete_document(cls, file_path: str) -> None:
        """Delete a document file from storage if it exists.

        Args:
            file_path: Stored document path.
        """
        p = Path(file_path)
        if p.exists() and p.is_file():
            os.remove(p)

    @classmethod
    def list_documents(cls) -> list[str]:
        """List all stored document filenames.

        Returns:
            List of filenames in storage.
        """
        storage_dir = cls._get_storage_path()
        return [str(f.name) for f in storage_dir.iterdir() if f.is_file()]
