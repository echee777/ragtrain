from abc import ABC, abstractmethod
import numpy as np
import torch
from torch.nn.functional import normalize
from transformers import AutoTokenizer, AutoModel
from threading import Lock
from typing import List
from sentence_transformers import SentenceTransformer




class Embedder(ABC):
    """Abstract base class for embedders"""

    def __init__(self):
        self._is_loaded = False

    @abstractmethod
    def start(self) -> None:
        """Load embedder model into memory"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Remove embedder model from memory"""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single text"""
        if not self._is_loaded:
            raise RuntimeError("Embedder must be started before embedding")

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        if not self._is_loaded:
            raise RuntimeError("Embedder must be started before embedding")

    @abstractmethod
    def get_keywords(self) -> List[str]:
        """Get keywords associated with this embedder"""
        pass

    @property
    def is_loaded(self) -> bool:
        """Check if embedder is loaded in memory"""
        return self._is_loaded



class BiobertEmbedder(Embedder):
    def __init__(self):
        super().__init__()
        self._lock = Lock()    # To support multithreaded access
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._keywords = [
            "cell", "DNA", "RNA", "protein", "gene",
            "enzyme", "mutation", "chromosome", "nucleus"
        ]

    def start(self) -> None:
        with self._lock:
            if not self._is_loaded:
                self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.2")
                self.model = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.2")
                self.model.to(self.device)
                self.model.eval()
                self._is_loaded = True

    def stop(self) -> None:
        with self._lock:
            if self._is_loaded:
                del self.model
                del self.tokenizer
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                self.model = None
                self.tokenizer = None
                self._is_loaded = False

    def embed(self, text: str) -> List[float]:
        """Get sentence embedding ([CLS] token) from BioBERT"""
        super().embed(text)  # Check if loaded
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        outputs = self.model(**inputs)
        # Get [CLS] token embedding and convert to list
        return outputs[0][0, 0, :].cpu().tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get sentence embeddings for multiple texts"""
        super().embed_batch(texts)  # Check if loaded
        inputs = self.tokenizer(texts, padding=True, return_tensors="pt").to(self.device)
        outputs = self.model(**inputs)
        # Get [CLS] token embeddings for each text and convert to list
        return outputs[0][:, 0, :].cpu().tolist()

    def get_keywords(self) -> List[str]:
        return self._keywords



class GeneralEmbedder(Embedder):
    """General purpose embedder using sentence-transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__()
        self.model_name = model_name
        self.model = None

        # General purpose keywords
        self._keywords = [
            "what", "how", "why", "explain",
            "compare", "contrast", "describe", "analyze",
            "define", "calculate", "solve", "discuss"
        ]

    def start(self) -> None:
        """Load the model into memory"""
        if not self._is_loaded:
            self.model = SentenceTransformer(self.model_name)
            self._is_loaded = True

    def stop(self) -> None:
        """Remove model from memory"""
        if self._is_loaded:
            self.model = None
            self._is_loaded = False

    def embed(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        super().embed(text)  # Check if loaded
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts"""
        super().embed_batch(texts)  # Check if loaded
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def get_keywords(self) -> List[str]:
        """Get general-purpose keywords"""
        return self._keywords