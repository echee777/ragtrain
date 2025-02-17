import openai
from typing import List
from ragtrain.types import PromptConfig
from ragtrain.template_manager import PromptManager
from ragtrain.embeddings import EmbeddingsManager


class HIPAgent:
    def __init__(self):
        self.embeddings_manager = EmbeddingsManager()
        self.prompt_manager = PromptManager()

    def get_response(self, question: str, answer_choices: List[str]) -> int:
        # For testbench.py compatibility - use default biology config
        config = self._create_default_biology_config()
        mcq = MCQ(
            id=str(hash(question)),
            question=question,
            answers=answer_choices,
            correct_answer=-1  # Unknown in this context
        )

        # Get multiple prompt variations
        prompts = self.prompt_manager.make_prompts(mcq, config)

        # Try each prompt and track scores
        best_score = -1
        best_answer = -1

        for prompt in prompts:
            response = self._query_llm(prompt)
            score, answer = self._evaluate_response(response)

            if score > best_score:
                best_score = score
                best_answer = answer

        return best_answer

    def _create_default_config(self) -> PromptConfig:
        return PromptConfig(
            mcq_file=
        )

    def _query_llm(self, prompt: str) -> str:
        pass

    def _evaluate_response(self, response: str) -> tuple[float, int]:
        pass