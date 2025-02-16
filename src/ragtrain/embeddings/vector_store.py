from abc import ABC, abstractmethod
from typing import List, Optional
from . import EmbeddingMatch
import chromadb
from chromadb.config import Settings



class VectorStore(ABC):
    @abstractmethod
    def add_embeddings(self, texts: List[str], embeddings: List[List[float]],
                       metadata: Optional[List[dict]] = None) -> None:
        """Add embeddings to the vector store"""
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], k: int) -> List[EmbeddingMatch]:
        """Search for similar embeddings"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all embeddings from the store"""
        pass


class ChromaVectorStore(VectorStore):
    """Vector store implementation using ChromaDB"""

    def __init__(self,
                 collection_name: str = "default",
                 persist_directory: Optional[str] = None,
                 get_or_create: bool = False):
        """Initialize ChromaDB client

        Args:
            collection_name: Name of the collection to use
            persist_directory: If provided, store data on disk at this location.
                             If None, use in-memory storage.
        """
        self._is_persistent = False
        if not persist_directory:
            settings = Settings(
                anonymized_telemetry=False,
                persist_directory=":memory:",
            )
            self.client = chromadb.Client(settings)
            self.collection = self.client.create_collection(name=collection_name)
        else:
            self._is_persistent = True
            settings = Settings(
                anonymized_telemetry=False,
                persist_directory=persist_directory,
                chroma_db_impl='duckdb+parquet',
            )
            self.client = chromadb.Client(settings)
            self.collection = self.client.create_collection(name=collection_name, get_or_create=get_or_create)

    def add_embeddings(self, texts: List[str], embeddings: List[List[float]], metadata: Optional[List[dict]] = None):
        if not texts or not embeddings:
            return

        # if metadata is None:
        #     metadata = [{} for _ in texts]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadata,
            ids=[f"id_{i}" for i in range(len(texts))]
        )
        if self._is_persistent:
            self.client.persist()

    def search(self, query_embedding: List[float], k: int) -> List[EmbeddingMatch]:
        if k <= 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # If no results found
        if not results['documents'][0]:
            return []

        matches = []
        for i in range(len(results['documents'][0])):
            match = EmbeddingMatch(
                content=results['documents'][0][i],
                # Chroma scores: lower number / lower distance
                # means better match.
                # Transform to best match = 1
                score=1-float(results['distances'][0][i]),
                metadata=results['metadatas'][0][i]
            )
            matches.append(match)

        return matches

    def clear(self):
        """Clear all data from the store"""
        self.collection.delete(where={})  # Delete all documents