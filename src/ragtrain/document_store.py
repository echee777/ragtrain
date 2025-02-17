# File: ragtrain/document_store.py

from abc import ABC, abstractmethod
from pathlib import Path
import os
import shutil
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class DocumentStore(ABC):
    """Abstract interface for document storage"""

    @abstractmethod
    def store_document(self, doc_hash: str, content: str, filename: Optional[str] = None) -> Path:
        """Store a document with given hash and content

        Args:
            doc_hash: Hash identifier for the document
            content: Document content to store
            filename: Optional filename, defaults to 'content.txt'

        Returns:
            Path where document was stored

        Raises:
            IOError: If storage fails
        """
        pass

    @abstractmethod
    def get_document(self, doc_hash: str, filename: Optional[str] = None) -> str:
        """Retrieve document content by hash

        Args:
            doc_hash: Hash identifier for the document
            filename: Optional filename, defaults to 'content.txt'

        Returns:
            Document content as string

        Raises:
            FileNotFoundError: If document not found
        """
        pass

    @abstractmethod
    def delete_document(self, doc_hash: str) -> None:
        """Delete document and its directory by hash

        Args:
            doc_hash: Hash identifier for the document

        Raises:
            FileNotFoundError: If document not found
        """
        pass

    @abstractmethod
    def list_documents(self) -> List[str]:
        """List all document hashes in store

        Returns:
            List of document hash IDs
        """
        pass


class FileSystemDocumentStore(DocumentStore):
    """Filesystem-based document store implementation"""

    def __init__(self, base_dir: Path):
        """Initialize with base directory

        Args:
            base_dir: Base directory for document storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_document(self, doc_hash: str, content: str, filename: Optional[str] = None) -> Path:
        """Store document in hash-based directory structure"""
        doc_dir = self.base_dir / doc_hash
        doc_dir.mkdir(exist_ok=True)

        file_path = doc_dir / (filename or 'content.txt')

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return file_path
        except IOError as e:
            logger.error(f"Failed to store document {doc_hash}: {str(e)}")
            raise

    def get_document(self, doc_hash: str, filename: Optional[str] = None) -> str:
        """Retrieve document content from hash directory"""
        file_path = self.base_dir / doc_hash / (filename or 'content.txt')

        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_hash}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            logger.error(f"Failed to read document {doc_hash}: {str(e)}")
            raise

    def delete_document(self, doc_hash: str) -> None:
        """Delete document directory and contents"""
        doc_dir = self.base_dir / doc_hash

        if not doc_dir.exists():
            raise FileNotFoundError(f"Document not found: {doc_hash}")

        try:
            shutil.rmtree(doc_dir)
        except IOError as e:
            logger.error(f"Failed to delete document {doc_hash}: {str(e)}")
            raise

    def list_documents(self) -> List[str]:
        """List all document hashes by directory names"""
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]