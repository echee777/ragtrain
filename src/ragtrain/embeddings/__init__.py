# Create a stable interface for the package regardless of
# internal organization.

# Import types before other symbols to avoid circular import issues
from .types import (SubjectDomain, EmbeddingMatch)

from .vector_store import VectorStore, ChromaVectorStore
from .embedders import (Embedder, BiobertEmbedder, GeneralEmbedder)
from .manager import EmbeddingsManager

__all__ = [
    'VectorStore',
    'ChromaVectorStore',
    'EmbeddingMatch',
    'Embedder',
    'BiobertEmbedder',
    'GeneralEmbedder',
    'SubjectDomain',
    'EmbeddingsManager'
]
