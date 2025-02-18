from enum import Enum, auto
from dataclasses import dataclass


@dataclass(order=True)
class EmbeddingMatch:
    """Represents a matched embedding with its similarity score"""
    score: float
    content: str
    metadata: dict
