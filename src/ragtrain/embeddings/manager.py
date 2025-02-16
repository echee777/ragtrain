from typing import Dict, List
import numpy as np
from . import Embedder, SubjectDomain, EmbeddingMatch
from .vector_store import VectorStore


class EmbeddingsManager:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.embedders: Dict[SubjectDomain, Embedder] = {}

    def register_embedder(self, domain: SubjectDomain, embedder: Embedder):
        """Register an embedder for a specific domain"""
        self.embedders[domain] = embedder

    def get_best_embedder(self, question: str) -> Embedder:
        """Get the most suitable embedder for a given question

        Uses the general embedder to evaluate similarity between the question
        and each embedder's keywords in a consistent embedding space.
        """
        general_embedder = self.embedders[SubjectDomain.GENERAL]
        best_score = -1
        best_embedder = None

        # Embed question using general embedder
        question_embedding = general_embedder.embed(question)

        for domain, embedder in self.embedders.items():
            # Use general embedder to evaluate all keywords
            keyword_embeddings = general_embedder.embed_batch(embedder.get_keywords())
            similarities = [self._cosine_similarity(question_embedding, ke) for ke in keyword_embeddings]
            score = max(similarities) if similarities else 0

            if score > best_score:
                best_score = score
                best_embedder = embedder

        return best_embedder or self.embedders[SubjectDomain.GENERAL]

    def create_embeddings(self, texts: List[str], domain: SubjectDomain):
        """Create and store embeddings for texts using the specified domain embedder

        Selects the appropriate embedded based on SubjectDomain
        """
        embedder = self.embedders[domain]
        embeddings = embedder.embed_batch(texts)
        self.vector_store.add_embeddings(texts, embeddings)

    def get_top_k_embeddings(self, k: int, domain: SubjectDomain, question: str) -> List[EmbeddingMatch]:
        """Get top k similar embeddings for a question in the specified domain

        Selects the appropriate embedded based on SubjectDomain
        """
        embedder = self.embedders[domain]
        query_embedding = embedder.embed(question)
        return self.vector_store.search(query_embedding, k)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))