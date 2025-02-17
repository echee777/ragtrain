# Create a stable interface for the package regardless of
# internal organization.

# Import types before other symbols to avoid circular import issues
from ragtrain.types import SubjectDomain
from ragtrain.constants import EMBEDDINGS_DIR
from .types import EmbeddingMatch

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
    'EmbeddingsManager'
]


@staticmethod
def get_default_embeddings_manager() -> EmbeddingsManager:
    """Create an EmbeddingsManager that supports specific subject domains"""
    biology_embedder = BiobertEmbedder()
    general_embedder = GeneralEmbedder()
    biology_embedder.start()
    general_embedder.start()

    biology_store = ChromaVectorStore(
        collection_name=SubjectDomain.BIOLOGY, get_or_create=True,
        persist_directory=str(EMBEDDINGS_DIR),
    )
    general_store = ChromaVectorStore(
        collection_name=SubjectDomain.GENERAL, get_or_create=True,
        persist_directory=str(EMBEDDINGS_DIR),
    )

    manager = EmbeddingsManager()
    manager.register_embedder(
        SubjectDomain.BIOLOGY, biology_embedder, biology_store)
    manager.register_embedder(
        SubjectDomain.GENERAL, general_embedder, general_store)
    return manager
