import hashlib
import os.path

import requests
from typing import Generator, List
from urllib.parse import urlparse
import logging

from ragtrain.constants import DOWNLOADS_DIR
from ragtrain.embeddings.manager import EmbeddingsManager
from ragtrain.document_store import DocumentStore

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

    def process_document(self, document_url: str, force_reprocess: bool = False) -> str:
        """Process a document from URL or local path

        Args:
            document_url: HTTP URL or local file path

        Returns:
            Document hash ID

        Raises:
            ValueError: If URL is invalid or document can't be processed
        """
        # Download and get content
        content = self.get_document_content(document_url)
        doc_hash = TrainingManager.calculate_hash(content)
        # Check if document already exists and is processed
        if not force_reprocess:
            try:
                # See if the document is already present
                content = self.document_store.get_document(doc_hash)
                logger.info(f"Document {document_url} (hash: {doc_hash}) already processed, skipping")
                return doc_hash
            except FileNotFoundError:
                pass
        elif force_reprocess:
            logger.info(f"Force reprocessing document {document_url} (hash: {doc_hash})")

        # Store raw document
        self.document_store.store_document(doc_hash, content)
        logger.info(f"Stored new document {document_url} with hash {doc_hash}")

        # Determine subject domain
        subject_domain = self.embeddings_manager.get_subject_domain(content[:1000])

        # Get appropriate embedder
        embedder = self.embeddings_manager.get_best_embedder(subject_domain)
        tokenizer = embedder.get_tokenizer()

        # Process chunks
        batch_size = 10
        batch = []
        chunk_count = 0
        for chunk in self._chunk_document(content, tokenizer):
            print(f'Chunk {chunk_count}: len = {len(chunk)}')
            batch.append(chunk)
            chunk_count += 1

            # Process batch when full
            if len(batch) >= batch_size:
                self.embeddings_manager.create_embeddings(batch, subject_domain)  # Batch processing
                batch = []  # Reset batch

        # Process remaining chunks if any
        if batch:
            self.embeddings_manager.create_embeddings(batch, subject_domain)


        logger.info(f"Created {chunk_count} chunk embeddings for document {doc_hash}")
        return doc_hash

    @staticmethod
    def get_document_content(document_url: str) -> str:
        """Get document content from URL or local path"""
        parsed_url = urlparse(document_url)

        if parsed_url.scheme in ('http', 'https'):
            # Download from web
            response = requests.get(document_url)
            response.raise_for_status()
            return response.text

        elif not parsed_url.scheme or parsed_url.scheme == 'file':
            # Read local file
            if parsed_url.scheme:
                file_path = parsed_url.path
            else:
                file_path = str(DOWNLOADS_DIR / document_url)
            with open(file_path, 'r') as f:
                return f.read()

        else:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")

    @staticmethod
    def calculate_hash(content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _chunk_document(self, content: str, tokenizer, max_length: int = 500, stride: int = 100) -> Generator[str, None, None]:
        """
        Chunk text into segments of approximately max_length tokens with overlap,
        ensuring no word truncation issues and efficient token management.

        Args:
            content (str): Input text to chunk.
            tokenizer: HuggingFace AutoTokenizer.
            max_length (int): Maximum token length per chunk (default: 500).
            stride (int): Number of tokens to overlap between chunks (default: 100).

        Yields:
            str: Text chunks.
        """

        # Tokenize the text while keeping track of word boundaries
        tokenized = tokenizer(
            content,
            add_special_tokens=False,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=max_length,
            stride=stride
        )

        # Iterate over chunks and decode them
        for chunk_tokens in tokenized['input_ids']:
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            if chunk_text.strip():
                yield chunk_text.strip()
