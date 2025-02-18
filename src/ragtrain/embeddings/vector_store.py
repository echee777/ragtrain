from abc import ABC, abstractmethod
from typing import List, Optional
from . import EmbeddingMatch
import chromadb
from chromadb.config import Settings
import uuid
import math


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

        sample_distances = results['distances'][0]
        if all(-1 <= d <= 1 for d in sample_distances):
            metric = "cosine"  # Cosine similarity has bounded distances [-1,1]
        elif all(d >= 0 for d in sample_distances) and max(sample_distances) > 2:
            metric = "l2"  # Euclidean distances are positive and can be large
        elif any(d < -1 for d in sample_distances):
            metric = "ip"  # Inner Product distances can be large and negative
        else:
            metric = "cosine"  # Default fallback assumption

        for i in range(len(results['documents'][0])):
            distance = float(results['distances'][0][i])

            # Normalize similarity scores for all metrics
            if metric == "cosine":
                # Cosine distance to similarity: d → 1-d
                score = 1 - distance
            elif metric == "l2":
                # L2 distance to similarity: d → exp(-d)
                # This gives score=1 when distance=0 and decays exponentially
                score = math.exp(-distance)
            elif metric == "ip":
                # For inner product, we need to know the theoretical bounds
                # This assumes the vectors have been normalized to unit length
                if -1 <= distance <= 1:
                    score = (distance + 1) / 2
                else:
                    # For unnormalized vectors, we use a sigmoid-like function
                    score = 1 / (1 + math.exp(-distance))

            # Ensure score is within [0,1]
            score = max(0, min(1, score))

            match = EmbeddingMatch(
                content=results['documents'][0][i],
                score=score,
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
