from typing import List, Dict, Optional, Tuple
import openai
import json
from ragtrain.types import MCQ, GPT_MODEL, PromptType, SubjectDomain
from ragtrain.schema.experiment import PromptConfig
from ragtrain.template_manager import TemplateManager
from ragtrain.constants import TEMPLATE_DIR
from ragtrain.prompt_manager import PromptManager
from ragtrain.embeddings import get_default_embeddings_manager
import os
import logging
from dataclasses import dataclass
from enum import Enum
from schema.experiment import PromptVersionConfig

logger = logging.getLogger(__name__)



class ResponseStrategy(str, Enum):
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
    def __init__(self):
        """Initialize the HIP agent

        Args:
            openai_api_key: OpenAI API key
            template_manager: Manager for template handling
            response_strategy: Strategy for selecting best response
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not set")

        # Create an embeddings manager
        self.embeddings_manager = get_default_embeddings_manager()

        # Create a template manager to inject into the prompt manager
        # Templates are for now stored on disk
        self.template_manager = TemplateManager(base_path=str(TEMPLATE_DIR))

        # Create a prompt manager for loading and materializing prompt templates
        self.prompt_manager = PromptManager(
            self.template_manager, embeddings_manager=self.embeddings_manager)

        # Choose the response strategy
        self.response_strategy = ResponseStrategy.HIGHEST_CONFIDENCE

        openai.api_key = self.openai_api_key


    @staticmethod
    def _get_default_prompt_config():
        """Default combination of prompts to try for every question"""
        return PromptConfig(
            prompt_template_dir=TEMPLATE_DIR,
            versions={
                PromptType.COT: PromptVersionConfig(version="1", enabled=True),
                PromptType.FEW_SHOT: PromptVersionConfig(version="1", enabled=True),
                PromptType.CONTRARIAN: PromptVersionConfig(version="1", enabled=True),
                PromptType.RAG: PromptVersionConfig(version="1", enabled=True)
            }
        )


    def get_response(self, question: str, answer_choices: List[str]) -> int:
        """Get response for a single question"""

        mcq = MCQ(
            id="temp",
            question=question,
            answers=answer_choices,
            correct_answer=-1  # No answer for this question
        )

        # Get instantiated prompts
        prompts = self.prompt_manager.make_prompts(mcq, HIPAgent._get_default_prompt_config())

        # Try each prompt
        results = []
        for prompt_type, instantiated_prompt in prompts.items():
            result = self._try_prompt(instantiated_prompt, mcq)
            if result:
                results.append(result)

        # Select best result
        print('All results = \n{results}\n\n')
        best_result = self._select_best_result(results).answer_index if results else -1
        print(f'Best result = \n{best_result}')
        return best_result


    def _try_prompt(self,
                    prompt: str,
                    prompt_type: PromptType,  # Swapped order to match usage
                    mcq: MCQ) -> Optional[AttemptResult]:
        """Try a single instantiated prompt with GPT"""
        try:
            functions = [{
                "name": "submit_mcq_answer",
                "description": "Submit a multiple choice answer with explanation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "integer",
                            "description": "The number of the correct answer (1-4)",
                            "enum": [1, 2, 3, 4]
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence in the answer from 0.0 to 1.0",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Detailed explanation of why this answer is correct"
                        }
                    },
                    "required": ["answer", "confidence", "reasoning"]
                }
            }]

            system_role_guide = """You are an expert MCQ solver..."""  # Your existing guide

            response = openai.ChatCompletion.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_role_guide},
                    {"role": "user", "content": prompt}
                ],
                functions=functions,
                function_call={"name": "submit_mcq_answer"},
                temperature=0.3
            )

            # Get function call results instead of message content
            function_response = response.choices[0].message.function_call
            if not function_response:
                return None

            result = json.loads(function_response.arguments)

            # Validate answer is in range
            answer_index = result.get('answer', -1) - 1  # Convert to 0-based index
            if not (0 <= answer_index < len(mcq.answers)):
                return None

            return AttemptResult(
                prompt_type=prompt_type,
                answer_index=answer_index,
                confidence=result.get('confidence', 0.0),
                reasoning=result.get('reasoning', ''),
                raw_response=function_response.arguments
            )

        except Exception as e:
            logger.error(f"Error with prompt {prompt_type}: {str(e)}")
            return None


    def _select_best_result(self, results: List[AttemptResult]) -> Optional[AttemptResult]:
        """Select best result based on response strategy"""
        if not results:
            return None

        if self.response_strategy == ResponseStrategy.HIGHEST_CONFIDENCE:
            return max(results, key=lambda x: x.confidence)

        elif self.response_strategy == ResponseStrategy.MAJORITY_VOTE:
            # Count votes for each answer
            votes = {}
            for result in results:
                votes[result.answer_index] = votes.get(result.answer_index, 0) + 1

            # Find answer with most votes
            max_votes = max(votes.values())
            winners = [ans for ans, count in votes.items() if count == max_votes]

            if len(winners) == 1:
                # Return the result with this answer and highest confidence
                winning_answer = winners[0]
                return max(
                    (r for r in results if r.answer_index == winning_answer),
                    key=lambda x: x.confidence
                )

        # Default to first valid
        return results[0]
