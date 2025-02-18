import os
import hashlib
import json
import openai
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple
from openai import OpenAIError, RateLimitError, APIError
from ragtrain.types import MCQ, GPT_MODEL, PromptType, SubjectDomain
from ragtrain.schema.experiment import PromptConfig, PromptVersionConfig
from ragtrain.template_manager import TemplateManager
from ragtrain.constants import TEMPLATE_DIR
from ragtrain.prompt_manager import PromptManager
from ragtrain.embeddings import get_default_embeddings_manager
from retrying import retry as retrying_retry
from pprint import pformat


logger = logging.getLogger(__name__)



class ResponseStrategy(str, Enum):
    """Strategy for selecting the best response from multiple attempts"""
    HIGHEST_CONFIDENCE = "highest_confidence"
    MAJORITY_VOTE = "majority_vote"
    MAJORITY_VOTE_WITH_CONFIDENCE = "majority_vote_with_confidence"


@dataclass
class AttemptResult:
    """Stores the result of a single prompt attempt"""
    prompt_type: PromptType
    answer_index: int
    confidence: float
    reasoning: str
    raw_response: str
    def __repr__(self):
        return f"prompt type={self.prompt_type}, answer_index={self.answer_index}, confidence={self.confidence}, reasoning={self.reasoning}\n"



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
            id=hashlib.sha256(question.encode()).hexdigest(),
            question=question,
            answers=answer_choices,
            correct_answer=-1  # No answer for this question
        )

        # Get instantiated prompts
        prompts = self.prompt_manager.make_prompts(mcq, HIPAgent._get_default_prompt_config())

        # Try each prompt
        results = []
        for prompt_type, instantiated_prompt in prompts.items():
            result = try_prompt(self.openai_api_key, instantiated_prompt, prompt_type, mcq)
            if result:
                results.append(result)

        # Select best result
        print("============================================================")
        print(f'Question: {mcq.question}\n')
        print("============================================================")
        for idx, answer in enumerate(mcq.answers):
            print(f'\t{idx}: {answer}\n')

        print(f'All results: \n{results}\n')
        best_result_index = select_best_result(self.response_strategy, results).answer_index if results else -1
        best_result_index -= 1 # convert to zero based
        print(f'Best result index = {best_result_index} , Best result = {mcq.answers[best_result_index]}')
        print('')
        return best_result_index



def should_retry_openai(exception):
    """Retry on RateLimitError and APIError"""
    return isinstance(exception, (RateLimitError, APIError))

@retrying_retry(
    retry_on_exception=should_retry_openai,
    wait_exponential_multiplier=1000,  # 1 second in milliseconds
    wait_exponential_max=60000,  # 60 seconds max
    stop_max_attempt_number=5
)
def try_prompt(openai_api_key: str,
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
                        "description": "The number of the correct answer (0-3)",
                        "enum": [0, 1, 2, 3]
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

        client = openai.OpenAI(api_key=openai_api_key)

        response = client.chat.completions.create(
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
        logger.error(f"Error with prompt {prompt_type} {prompt[:50]}: {str(e)}")
        return None


def select_best_result(response_strategy: ResponseStrategy, results: List[AttemptResult]) -> Optional[AttemptResult]:
    """Select best result based on response strategy.

    Args:
        results: List of AttemptResult objects containing answer_index and confidence

    Returns:
        The selected AttemptResult based on the strategy, or None if no valid result

    Strategy behaviors:
        HIGHEST_CONFIDENCE: Simply returns attempt with highest confidence
        MAJORITY_VOTE: Uses pure democracy, breaks ties with first answer
        MAJORITY_VOTE_WITH_CONFIDENCE: Uses weighted voting based on confidence
    """
    if not results:
        return None

    if response_strategy == ResponseStrategy.HIGHEST_CONFIDENCE:
        return max(results, key=lambda x: x.confidence)

    elif response_strategy == ResponseStrategy.MAJORITY_VOTE:
        # Count votes for each answer
        votes: Dict[int, int] = {}
        for result in results:
            votes[result.answer_index] = votes.get(result.answer_index, 0) + 1

        # Find answer(s) with most votes
        max_votes = max(votes.values())
        winners = [ans for ans, count in votes.items() if count == max_votes]

        if len(winners) == 1:
            # Clear winner - return highest confidence result with this answer
            winning_answer = winners[0]
            matching_results = [r for r in results if r.answer_index == winning_answer]
            return max(matching_results, key=lambda x: x.confidence)
        else:
            # Tie - break by taking highest confidence among tied answers
            tied_results = [r for r in results if r.answer_index in winners]
            return max(tied_results, key=lambda x: x.confidence)

    elif response_strategy == ResponseStrategy.MAJORITY_VOTE_WITH_CONFIDENCE:
        # Weight votes by confidence
        weighted_votes: Dict[int, float] = {}
        for result in results:
            weighted_votes[result.answer_index] = (
                    weighted_votes.get(result.answer_index, 0) + result.confidence
            )

        # Return result matching answer with highest weighted votes
        winning_answer = max(weighted_votes.items(), key=lambda x: x[1])[0]
        matching_results = [r for r in results if r.answer_index == winning_answer]
        return max(matching_results, key=lambda x: x.confidence)

    else:
        raise ValueError(f"Unknown response strategy: {response_strategy}")



