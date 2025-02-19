from typing import Dict, List, Tuple
import numpy as np
from ragtrain.types import SubjectDomain
from . import Embedder, EmbeddingMatch
from .vector_store import VectorStore
from datetime import datetime


class EmbeddingsManager:
    def __init__(self):
        self.embedders: Dict[SubjectDomain, Embedder] = {}
        self.vector_stores: Dict[SubjectDomain, VectorStore] = {}

    def register_embedder(self, domain: SubjectDomain, embedder: Embedder, vector_store: VectorStore):
        """Register an embedder for a specific domain"""
        self.embedders[domain] = embedder
        self.vector_stores[domain] = vector_store


    def _get_best_embedder(self, text: str) -> Tuple[SubjectDomain, Embedder]:
        general_embedder = self.embedders[SubjectDomain.GENERAL]
        best_score = -1
        best_embedder = None
        best_domain = None

        # Embed text using general embedder
        question_embedding = general_embedder.embed(text)

        for domain, embedder in self.embedders.items():
            # Use general embedder to evaluate all keywords
            keyword_embeddings = general_embedder.embed_batch(embedder.get_keywords())
            similarities = [self._cosine_similarity(question_embedding, ke) for ke in keyword_embeddings]
            score = max(similarities) if similarities else 0

            if score > best_score:
                best_score = score
                best_embedder = embedder
                best_domain = domain
        return (best_domain, best_embedder)


    def get_subject_domain(self, text) -> SubjectDomain:
        """Classify the input text as one of the supported SubjectDomains.

        There is a 1-1 relationship between SubjectDomain and supported Embedder.

        Uses the general embedder to evaluate similarity between the question
        and each embedder's keywords in a consistent embedding space.
        """
        domain, _ = self._get_best_embedder(text)
        return domain


    def get_best_embedder(self, question: str) -> Embedder:
        """Get the most suitable embedder for a given question

        Uses the general embedder to evaluate similarity between the question
        and each embedder's keywords in a consistent embedding space.
        """
        _, embedder = self._get_best_embedder(question)
        return embedder

    def create_embeddings(self, texts: List[str], domain: SubjectDomain):
        """Create and store embeddings for texts using the specified domain embedder

        Selects the appropriate embedded based on SubjectDomain
        """
        embedder = self.embedders[domain]
        embeddings = embedder.embed_batch(texts)

        # Create metadata for each chunk
        metadata = [{
            "domain": domain.value,
            "timestamp": datetime.utcnow().isoformat(),
            "embedder": embedder.__class__.__name__
        } for _ in texts]

        self.vector_stores[domain].add_embeddings(texts, embeddings, metadata=metadata)

    def get_top_k_embeddings(self, k: int, domain: SubjectDomain, question: str) -> List[EmbeddingMatch]:
        """Get top k similar embeddings for a question in the specified domain

        Selects the appropriate embedded based on SubjectDomain
        """
        embedder = self.embedders[domain]
        query_embedding = embedder.embed(question)
        return self.vector_stores[domain].search(query_embedding, k)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))