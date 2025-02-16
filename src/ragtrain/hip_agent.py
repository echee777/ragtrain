from typing import List, Dict, Optional, Tuple
import openai
from ragtrain.types import MCQ, PromptConfig, PromptType, TestResult
from ragtrain.prompt_templates import TemplateManager, PromptManager
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseStrategy(Enum):
    """Strategy for selecting the best response from multiple attempts"""
    HIGHEST_CONFIDENCE = "highest_confidence"
    MAJORITY_VOTE = "majority_vote"
    FIRST_VALID = "first_valid"


@dataclass
class AttemptResult:
    """Stores the result of a single prompt attempt"""
    prompt_type: PromptType
    answer_index: int
    confidence: float
    reasoning: str
    raw_response: str


class HIPAgent:
    def __init__(self,
                 openai_api_key: str,
                 template_manager: TemplateManager,
                 response_strategy: ResponseStrategy = ResponseStrategy.HIGHEST_CONFIDENCE):
        """Initialize the HIP agent

        Args:
            openai_api_key: OpenAI API key
            template_manager: Manager for template handling
            response_strategy: Strategy for selecting best response
        """
        self.openai_api_key = openai_api_key
        self.prompt_manager = PromptManager(template_manager)
        self.response_strategy = response_strategy

        openai.api_key = openai_api_key

    def get_response(self, question: str, answer_choices: List[str]) -> int:
        """Get response for a single question"""
        # Create MCQ and config
        mcq = MCQ(
            id="temp",
            question=question,
            answers=answer_choices,
            correct_answer=-1
        )
        config = self._create_default_config()

        # Get instantiated prompts
        prompts = self.prompt_manager.make_prompts(mcq, config)

        # Try each prompt
        results = []
        for prompt_type, instantiated_prompt in prompts.items():
            result = self._try_prompt(instantiated_prompt, mcq)
            if result:
                results.append(result)

        # Select best result
        return self._select_best_result(results).answer_index if results else -1

    def _try_prompt(self,
                    instantiated_prompt: InstantiatedPrompt,
                    mcq: MCQ) -> Optional[AttemptResult]:
        """Try a single instantiated prompt

        Now HIPAgent only needs to handle LLM interaction and response parsing,
        not template handling
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert tutor..."},
                    {"role": "user", "content": instantiated_prompt.content},
                ],
                temperature=0.3
            )

            response_text = response.choices[0].message.content
            answer_index, confidence, reasoning = self._parse_response(response_text, mcq)

            if answer_index >= 0:
                return AttemptResult(
                    prompt_type=instantiated_prompt.prompt_type,
                    answer_index=answer_index,
                    confidence=confidence,
                    reasoning=reasoning,
                    raw_response=response_text
                )

        except Exception as e:
            print(f"Error with prompt {instantiated_prompt.prompt_type}: {str(e)}")

        return None