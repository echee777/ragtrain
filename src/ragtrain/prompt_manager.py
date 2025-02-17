import tiktoken
from typing import Dict, Any
from string import Template
from ragtrain.types import PromptType, MCQ, SubjectDomain, GPT_MODEL, GPT_MODEL_MAX_TOKENS
from ragtrain.schema.experiment import PromptConfig
from ragtrain.template_manager import TemplateManager
from ragtrain.embeddings.manager import EmbeddingsManager


class PromptManager:
    """Manages loading and filling prompt templates"""

    def __init__(
            self,
            template_manager: TemplateManager,
            embeddings_manager: EmbeddingsManager
    ):
        """Initialize with template and embeddings managers

        Args:
            template_manager: Manager for loading templates
            embeddings_manager: Manager for embeddings and domain detection
        """
        self.template_manager = template_manager
        self.embeddings_manager = embeddings_manager
        self.encoder = tiktoken.encoding_for_model(GPT_MODEL)


    def make_prompts(self, mcq: MCQ, config: PromptConfig) -> Dict[PromptType, str]:
        """Generate prompts for each enabled prompt type

        Args:
            mcq: Multiple choice question to create prompts for
            config: Prompt configuration specifying which types to generate

        Returns:
            Dict mapping PromptType to filled prompt string for each enabled type

        Raises:
            ValueError: If any required variables are missing from the template
            FileNotFoundError: If any required templates are not found
        """
        prompts = {}
        variables = self._prepare_variables(mcq)
        subject_domain = self.embeddings_manager.get_subject_domain(mcq.question)
        max_chunks = 4   # TODO: Plumb this from the experiment.

        for prompt_type, version_config in config.versions.items():
            if not version_config.enabled:
                continue

            # Load template for detected subject domain
            template = self.template_manager.get_template(
                subject=subject_domain.value,
                template_type=prompt_type,
                version=version_config.version
            )
            num_tokens_template = self.count_tokens(template)


            if prompt_type == PromptType.RAG:
                self._prepare_rag_content(mcq, subject_domain, max_chunks,
                                          GPT_MODEL_MAX_TOKENS - num_tokens_template, variables)

            # Substitute variables
            try:
                prompts[prompt_type] = Template(template).substitute(variables)
            except KeyError as e:
                raise ValueError(f"Missing required variable {e.args[0]} "
                                 f"for {prompt_type.value} template")

        return prompts

    def _prepare_variables(self, mcq: MCQ) -> Dict[str, Any]:
        """Prepare variables for template substitution

        Args:
            mcq: Multiple choice question

        Returns:
            Dict of variables to substitute into templates
        """
        formatted_choices = "\n".join(
            f"{i + 1}. {choice}" for i, choice in enumerate(mcq.answers)
        )

        return {
            "question": mcq.question,
            "formatted_choices": formatted_choices,
        }


    def _prepare_rag_content(self, mcq: MCQ, subject_domain, num_chunks, max_tokens, variables) -> Dict[str, Any]:
        """Adds a substitution variable for rag content
        """
        # Obtain rag chunks from the appropriate embeddings
        chunks = self.embeddings_manager.get_top_k_embeddings(num_chunks, subject_domain, mcq.question)

        # If there were 0 non-general chunks, fallback to general chunks
        if len(chunks) == 0 and subject_domain != SubjectDomain.GENERAL:
            chunks = self.embeddings_manager.get_top_k_embeddings(num_chunks, SubjectDomain.GENERAL, mcq.question)

        rag_chunks = 'NO RAG CHUNKS FOUND'
        if len(chunks) > 0:
            rag_chunks = "\n\nHere is another RAG chunk\n\n".join(chunks)
            rag_chunks = self.truncate_to_tokens(rag_chunks, max_tokens)

        variables['rag_chunks'] = rag_chunks


    def count_tokens(self, text: str) -> int:
        """Count tokens using the same tokenizer as GPT-3.5"""
        return len(self.encoder.encode(text))


    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within max_tokens.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens allowed
            model: Model name to use for tokenization (default: gpt-3.5-turbo)

        Returns:
            Truncated text that fits within max_tokens
        """
        tokens = self.encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text

        # Truncate tokens and decode back to string
        truncated_tokens = tokens[:max_tokens]
        return self.encoder.decode(truncated_tokens)
