import hashlib
import os
from pathlib import Path
import requests
from typing import Generator, List
from urllib.parse import urlparse
import logging

from ragtrain.types import SubjectDomain
from ragtrain.embeddings.manager import EmbeddingsManager
from ragtrain.document_store import DocumentStore
from ragtrain.embeddings.vector_store import VectorStore

logger = logging.getLogger(__name__)


class TrainingManager:
    """Manages document training pipeline including downloading, chunking, and embedding"""

    def __init__(
            self,
            embeddings_manager: EmbeddingsManager,
            document_store: DocumentStore,
            max_chunk_tokens: int = 512
    ):
        """Initialize training manager

        Args:
            embeddings_manager: Manager for embeddings and domain detection
            vector_store: Store for document embeddings
            document_store: Store for raw documents
            max_chunk_tokens: Maximum tokens per chunk
        """
        self.embeddings_manager = embeddings_manager
        self.document_store = document_store
        self.max_chunk_tokens = max_chunk_tokens

    def process_document(self, document_url: str) -> str:
        """Process a document from URL or local path

        Args:
            document_url: HTTP URL or local file path

        Returns:
            Document hash ID

        Raises:
            ValueError: If URL is invalid or document can't be processed
        """
        # Download and store document
        content = self._get_document_content(document_url)
        doc_hash = self._calculate_hash(content)

        # Store raw document
        self.document_store.store_document(doc_hash, content)

        # Determine subject domain
        subject_domain = self.embeddings_manager.get_subject_domain(
            content[:1000])  # Use first 1000 chars for domain detection

        # Get appropriate embedder
        embedder = self.embeddings_manager.get_best_embedder(subject_domain)
        tokenizer = embedder.get_tokenizer()

        # Process chunks
        for chunk in self._chunk_document(content, tokenizer):
            # Store in vector database
            self.embeddings_manager.create_embeddings([chunk], subject_domain)

        return doc_hash

    def _get_document_content(self, document_url: str) -> str:
        """Get document content from URL or local path"""
        parsed_url = urlparse(document_url)

        if parsed_url.scheme in ('http', 'https'):
            # Download from web
            response = requests.get(document_url)
            response.raise_for_status()
            return response.text

        elif not parsed_url.scheme or parsed_url.scheme == 'file':
            # Read local file
            file_path = document_url if not parsed_url.scheme else parsed_url.path
            with open(file_path, 'r') as f:
                return f.read()

        else:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _chunk_document(self, content: str, tokenizer) -> Generator[str, None, None]:
        """Chunk document into fixed-size pieces based on token count

        Args:
            content: Text content to chunk
            tokenizer: HuggingFace AutoTokenizer instance

        Yields:
            Document chunks that respect token limits
        """
        # Encode the entire text
        encoded = tokenizer.encode(content, add_special_tokens=False)

        # Use sliding window with overlap
        stride = int(self.max_chunk_tokens * 0.1)  # 10% overlap
        start_idx = 0

        while start_idx < len(encoded):
            # Get chunk of tokens
            end_idx = min(start_idx + self.max_chunk_tokens, len(encoded))
            chunk_tokens = encoded[start_idx:end_idx]

            # Decode back to text
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)

            yield chunk_text.strip()

            # Move window, accounting for stride
            start_idx += self.max_chunk_tokens - stride