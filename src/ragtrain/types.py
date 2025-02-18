# mcq.py
from dataclasses import dataclass
from typing import List, Set
import hashlib
import json
from enum import Enum, auto


GPT_MODEL = "gpt-3.5-turbo-0125"

GPT_MODEL_MAX_TOKENS = 16385


class SubjectDomain(str, Enum):
    """Supported subject domains"""
    BIOLOGY = "biology"
    GENERAL = "general"


@dataclass
class MCQ:
    id: str
    question: str
    answers: List[str]
    correct_answer: int

    def __post_init__(self):
        # Create hash based on question content
        content = json.dumps({
            'question': self.question,
            'answers': self.answers,
            'correct_answer': self.correct_answer
        }, sort_keys=True)
        self.hash_id = hashlib.sha256(content.encode()).hexdigest()


@dataclass
class MCQList:
    questions: List[MCQ]

    def __post_init__(self):
        # Create hash based on all question hashes
        content = json.dumps([q.hash_id for q in self.questions], sort_keys=True)
        self.hash_id = hashlib.sha256(content.encode()).hexdigest()


@dataclass
class TestResult:
    mcq_list_hash: str
    incorrect_questions: List[str]  # List of question IDs
    total_questions: int
    score: int



class PromptType(str, Enum):
    """Types of prompts that can be generated"""
    COT = "cot"  # Chain of thought
    FEW_SHOT = "few_shot"  # Few shot examples
    CONTRARIAN = "contrarian"  # Contrarian perspective
    RAG = "rag"  # Rag
    PLAIN = "plain"

    @classmethod
    def all_types(cls) -> Set[str]:
        """Get all prompt type values"""
        return {e.value for e in cls}
