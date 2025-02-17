from abc import ABC, abstractmethod
from typing import List, Optional
from . import EmbeddingMatch
import chromadb
from chromadb.config import Settings
import uuid



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

    @abstractmethod
    def reset(self):
        """Reset all connections / resources"""
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
            self.client = chromadb.EphemeralClient()
            self.collection = self.client.create_collection(name=collection_name, get_or_create=get_or_create)
        else:
            self._is_persistent = True
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.create_collection(name=collection_name, get_or_create=get_or_create)

    def add_embeddings(self, texts: List[str], embeddings: List[List[float]], metadata: Optional[List[dict]] = None):
        """Add embeddings to the vector store

        Args:
            texts: List of text chunks
            embeddings: List of embedding vectors
            metadata: Optional list of metadata dicts for each text
        """
        if not texts or not embeddings:
            return

        # Ensure valid metadata for ChromaDB
        if metadata is None:
            # Provide at least one metadata field as required by ChromaDB
            metadata = [{"source": "document"} for _ in texts]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadata,
            ids=[f"chunk_{uuid.uuid4()}" for _ in texts]
        )

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
        """Clear all data from the store by fetching all IDs and deleting them."""
        all_docs = self.collection.get()  # Fetch all documents
        if all_docs and "ids" in all_docs and all_docs["ids"]:
            self.collection.delete(ids=all_docs["ids"])  # Delete by ID

    def reset(self):
        print(f'Resetting chroma client: {id(self.client)}')
        self.client.reset()
