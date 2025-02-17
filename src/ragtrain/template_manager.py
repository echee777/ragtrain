from pathlib import Path
from typing import Dict, List, Optional
from ragtrain.types import PromptType


from ragtrain.types import PromptConfig, MCQ, PromptType, SubjectDomain
from pathlib import Path
from typing import Dict, List
import json


class PromptManager:
    def __init__(self):
        self.template_base_path = "templates"

    def make_prompts(self, mcq: MCQ, config: PromptConfig) -> Dict[PromptType, str]:
        """Generate multiple prompt variations

        Args:
            mcq: MCQ object containing question and answers
            config: Configuration for prompt generation

        Returns:
            Dict mapping PromptType to generated prompt string
        """
        # Base prompt with RAG chunks
        base_prompt = self._create_base_prompt(mcq, config)

        # Generate all variations
        prompts = {}

        # Chain of thought prompt
        if config.cot_template:
            prompts[PromptType.COT] = self._enhance_with_cot(base_prompt, config)

        # Few shot prompt
        if config.few_shot_template:
            prompts[PromptType.FEW_SHOT] = self._enhance_with_few_shot(base_prompt, config)

        # Combined COT + Few shot
        if config.cot_template and config.few_shot_template:
            prompts[PromptType.COT_FEW_SHOT] = self._enhance_with_cot_and_few_shot(base_prompt, config)

        # Contrarian prompt
        prompts[PromptType.CONTRARIAN] = self._create_contrarian_prompt(base_prompt, config)

        return prompts

    def _create_base_prompt(self, mcq: MCQ, config: PromptConfig) -> str:
        """Create base prompt including RAG context if available"""
        # Format question and answers
        question_text = f"Question: {mcq.question}\n\n"
        answers_text = "Possible answers:\n"
        for i, answer in enumerate(mcq.answers):
            answers_text += f"{chr(65 + i)}. {answer}\n"

        # Add RAG context if available
        rag_context = ""
        if config.rag_chunk_ids and config.rag_template:
            # TODO: Fetch actual chunks using IDs
            # For now, just note that RAG would be included
            rag_context = "Relevant context from materials:\n[RAG chunks would be inserted here]\n\n"

        # Build instruction
        instruction = """Please analyze this multiple choice question and provide your answer in JSON format with the following fields:
- answer: The full text of your chosen answer
- confidence: A number between 0 and 1 indicating your confidence
- reasoning: A brief explanation of your reasoning

Example response format:
{
    "answer": "Full text of selected answer",
    "confidence": 0.85,
    "reasoning": "Explanation of why this answer was chosen"
}
"""

        return f"{rag_context}{question_text}{answers_text}\n{instruction}"

    def _enhance_with_cot(self, base_prompt: str, config: PromptConfig) -> str:
        """Add chain-of-thought enhancement to prompt"""
        cot_instruction = """
Let's approach this step-by-step:
1. First, understand what the question is asking
2. Identify key concepts and terms
3. Consider each answer choice carefully
4. Eliminate obviously incorrect options
5. Analyze remaining choices in detail
6. Make a final selection with explanation

Please show your work for each step before providing your final answer in the requested JSON format.
"""
        return f"{base_prompt}\n{cot_instruction}"

    def _enhance_with_few_shot(self, base_prompt: str, config: PromptConfig) -> str:
        """Add few-shot examples to prompt"""
        # TODO: Load actual few-shot examples from template
        few_shot_examples = """
Here are some similar examples:

Example 1:
Q: What is the primary function of mitochondria in a cell?
A. Store genetic material
B. Produce energy through ATP
C. Break down proteins
D. Create cell membrane

Analysis:
- Mitochondria are known as the "powerhouse" of the cell
- Their main function is energy production
- They generate ATP through cellular respiration
- Other options describe functions of different organelles

{
    "answer": "Produce energy through ATP",
    "confidence": 0.95,
    "reasoning": "Mitochondria's primary and well-established function is ATP production"
}

Now please solve the current question following a similar analytical approach.
"""
        return f"{few_shot_examples}\n{base_prompt}"

    def _enhance_with_cot_and_few_shot(self, base_prompt: str, config: PromptConfig) -> str:
        """Combine chain-of-thought and few-shot enhancements"""
        few_shot = self._enhance_with_few_shot(base_prompt, config)
        return self._enhance_with_cot(few_shot, config)

    def _create_contrarian_prompt(self, base_prompt: str, config: PromptConfig) -> str:
        """Create a prompt that encourages challenging initial assumptions"""
        contrarian_instruction = """
Before selecting an answer, please:
1. Challenge your initial assumptions
2. Consider counterarguments for each possible answer
3. Look for edge cases or exceptions
4. Question whether the seemingly obvious answer could be a distractor
5. Verify that your choice isn't based on common misconceptions

After this critical analysis, provide your final answer in the requested JSON format.
"""
        return f"{base_prompt}\n{contrarian_instruction}"


class TemplateManager:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._validate_general_templates()

    def _validate_general_templates(self):
        """Validate that all required general templates exist"""
        for template_type in PromptType:
            general_path = self.base_path / SubjectDomain.GENERAL / template_type.value / "v1.txt"
            if not general_path.exists():
                raise FileNotFoundError(
                    f"Required general template missing: {general_path}. "
                    "General templates must be present for fallback functionality."
                )

    def get_template(self, subject: str, template_type: PromptType, version: str) -> str:
        """Get template content with fallback to general templates

        Args:
            subject: Subject domain (e.g. "biology")
            template_type: PromptType enum value
            version: Version string (e.g. "1")

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template doesn't exist and subject isn't valid for fallback
        """
        # For GENERAL domain, only look in general templates
        if subject.lower() == SubjectDomain.GENERAL:
            return self._get_general_template(template_type, version)

        # Check if subject directory exists
        subject_dir = self.base_path / subject.lower()
        if not subject_dir.exists():
            raise FileNotFoundError(f"Subject directory not found: {subject}")

        # For known subjects, try specific template then fallback
        if subject.lower() in [d.lower() for d in [SubjectDomain.BIOLOGY]]:
            try:
                return self._get_template_content(subject, template_type, version)
            except FileNotFoundError:
                return self._get_general_template(template_type, version)
        else:
            # For unknown subjects, don't fallback
            return self._get_template_content(subject, template_type, version)

    def _get_general_template(self, template_type: PromptType, version: str) -> str:
        """Get content of a general template"""
        template_path = (self.base_path / SubjectDomain.GENERAL /
                         template_type.value / f"v{version}.txt")
        if not template_path.exists():
            raise FileNotFoundError(f"General template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()

    def _get_template_content(self, subject: str, template_type: PromptType, version: str) -> str:
        """Get content of a specific template file"""
        template_path = self.base_path / subject.lower() / template_type.value / f"v{version}.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()

    def list_templates(self, subject: str = None) -> Dict[str, Dict[PromptType, List[str]]]:
        """List available templates including fallbacks

        Args:
            subject: Optional subject to filter by

        Returns:
            Dict mapping subject -> PromptType -> list of versions
        """
        result = {}

        if subject:
            subject = subject.lower()
            result[subject] = {}

            # For known subjects, add both specific and fallback templates
            if subject in [d.lower() for d in [SubjectDomain.BIOLOGY]]:
                # Get general templates for fallbacks
                general_templates = {}
                general_dir = self.base_path / SubjectDomain.GENERAL
                if general_dir.exists():
                    for prompt_type in PromptType:
                        type_dir = general_dir / prompt_type.value
                        if type_dir.exists():
                            versions = [p.stem.replace('v', '') for p in type_dir.glob('v*.txt')]
                            if versions:
                                general_templates[prompt_type] = versions

                # Add subject-specific templates
                subject_dir = self.base_path / subject
                if subject_dir.exists():
                    for prompt_type in PromptType:
                        type_dir = subject_dir / prompt_type.value
                        specific_versions = []
                        if type_dir.exists():
                            specific_versions = [p.stem.replace('v', '') for p in type_dir.glob('v*.txt')]

                        # Add both specific and fallback versions
                        if prompt_type in general_templates or specific_versions:
                            result[subject][prompt_type] = specific_versions.copy()
                            if prompt_type in general_templates:
                                result[subject][prompt_type].extend(
                                    [f"{v}(fallback)" for v in general_templates[prompt_type]]
                                )
                else:
                    # If subject dir doesn't exist, just add fallbacks
                    for prompt_type, versions in general_templates.items():
                        result[subject][prompt_type] = [f"{v}(fallback)" for v in versions]

        else:
            # List all templates
            for path in self.base_path.rglob('v*.txt'):
                parts = path.relative_to(self.base_path).parts
                if len(parts) != 3:  # subject/type/version.txt
                    continue

                curr_subject = parts[0]
                try:
                    template_type = PromptType(parts[1])
                except ValueError:
                    continue
                version = path.stem.replace('v', '')

                if curr_subject not in result:
                    result[curr_subject] = {}
                if template_type not in result[curr_subject]:
                    result[curr_subject][template_type] = []

                result[curr_subject][template_type].append(version)

        return result