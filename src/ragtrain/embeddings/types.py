from enum import Enum, auto
from dataclasses import dataclass


@dataclass
class EmbeddingMatch:
    """Represents a matched embedding with its similarity score"""
    content: str
    score: float
    metadata: dict
