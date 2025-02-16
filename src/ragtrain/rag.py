from typing import List, Optional, Dict
import tiktoken
from sentence_transformers import SentenceTransformer
from ragtrain.store.hiearchical_embedding_store import HierarchicalEmbeddingStore
import uuid
import io
import json
from pathlib import Path
import asyncio
from datetime import datetime


class RagTrainer:
    """
    Handles document processing and embedding creation.
    Uses synchronous code but can work with async embedding store.
    """

    def __init__(
            self,
            embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2",
            chunk_size: int = 500,
            chunk_overlap: int = 50,
            store_dir: str = "./embedding_store",
            buffer_size: int = 1024 * 1024,  # 1MB buffer
    ):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.chunk_size = chunk_sizel
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.store_dir = Path(store_dir)
        self.embedding_store = HierarchicalEmbeddingStore(str(self.store_dir))
        self.buffer_size = buffer_size
        self.docs_metadata_path = self.store_dir / "docs_metadata.json"
        self.docs_metadata = self._load_docs_metadata()

        # Create event loop for async operations
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    def _run_async(self, coro):
        """
        Helper method to run async code from sync context.
        Handles both running and not-running event loops.
        """
        try:
            # If we're in a running event loop, create a future
            if self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, self._loop)
                return future.result()
            # If no running event loop, run directly
            else:
                return self._loop.run_until_complete(coro)
        except Exception as e:
            print(f"Error running async code: {e}")
            raise

    def _load_docs_metadata(self) -> Dict[str, Dict]:
        """Load document metadata from disk."""
        if self.docs_metadata_path.exists():
            with self.docs_metadata_path.open('r') as f:
                return json.load(f)
        return {}

    def _save_docs_metadata(self):
        """Save document metadata to disk."""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.docs_metadata_path.open('w') as f:
            json.dump(self.docs_metadata, f, indent=2)

    def _create_chunks_from_buffer(self, text: str, partial_chunk: str, is_final: bool = False) -> tuple[
        List[str], str]:
        """Split buffer text into chunks."""
        text = partial_chunk + text
        chunks = []
        tokens = self.tokenizer.encode(text)

        start_idx = 0
        while start_idx + self.chunk_size < len(tokens):
            chunk_tokens = tokens[start_idx:start_idx + self.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            start_idx += (self.chunk_size - self.chunk_overlap)

        if is_final and start_idx < len(tokens):
            remaining_tokens = tokens[start_idx:]
            remaining_text = self.tokenizer.decode(remaining_tokens)
            chunks.append(remaining_text)
            new_partial_chunk = ""
        else:
            remaining_tokens = tokens[start_idx:]
            new_partial_chunk = self.tokenizer.decode(remaining_tokens)

        return chunks, new_partial_chunk

    def process_text_stream(
            self,
            text_stream: io.TextIOBase,
            doc_id: Optional[str] = None,
            metadata: Optional[Dict] = None
    ) -> str:
        """Process a text stream, storing chunks using async embedding store."""
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        doc_metadata = {
            "id": doc_id,
            "num_chunks": 0,
            "created_at": str(datetime.now()),
            **(metadata or {})
        }

        chunk_index = 0
        partial_chunk = ""
        batch_chunks: List[Chunk] = []
        BATCH_SIZE = 10

        while True:
            buffer = text_stream.read(self.buffer_size)
            is_final = len(buffer) < self.buffer_size

            if buffer or is_final:
                chunks, partial_chunk = self._create_chunks_from_buffer(
                    buffer, partial_chunk, is_final
                )

                # Create chunk objects
                for chunk_text in chunks:
                    # Create embedding
                    embedding = self.embedding_model.encode(chunk_text, convert_to_tensor=False)

                    chunk = {
                        "id": f"{doc_id}_chunk_{chunk_index}",
                        "text": chunk_text,
                        "embedding": embedding.tolist(),
                        "doc_id": doc_id,
                        "chunk_index": chunk_index,
                        "metadata": {}
                    }
                    batch_chunks.append(chunk)
                    chunk_index += 1

                    # Store batch if it's full
                    if len(batch_chunks) >= BATCH_SIZE:
                        # Use async store_chunks via run_async helper
                        result = self._run_async(
                            self.embedding_store.astore_chunks(batch_chunks)
                        )
                        if result["failed"]:
                            for idx in result["failed"]:
                                print(f"Failed to store chunk {batch_chunks[idx]['id']}")
                        batch_chunks = []

            if is_final:
                # Store any remaining chunks
                if batch_chunks:
                    result = self._run_async(
                        self.embedding_store.astore_chunks(batch_chunks)
                    )
                    if result["failed"]:
                        for idx in result["failed"]:
                            print(f"Failed to store chunk {batch_chunks[idx]['id']}")
                break

        # Update and save document metadata
        doc_metadata["num_chunks"] = chunk_index
        self.docs_metadata[doc_id] = doc_metadata
        self._save_docs_metadata()

        return doc_id

    def process_file(
            self,
            file_path: str,
            doc_id: Optional[str] = None,
            metadata: Optional[Dict] = None
    ) -> str:
        """Process a document file."""
        if metadata is None:
            metadata = {}

        file_path = Path(file_path)
        file_metadata = {
            "filename": file_path.name,
            "file_size": file_path.stat().st_size,
            **metadata
        }

        with open(file_path, 'r', encoding='utf-8') as f:
            return self.process_text_stream(f, doc_id, file_metadata)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Clean up async resources
        self._run_async(self.embedding_store.aclose())
        self._loop.close()

    def get_embedding_store(self):
        """Get the embedding store instance."""
        return self.embedding_store