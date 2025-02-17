import os
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tiktoken

from ragtrain.schema.experiment import PromptVersionConfig, PromptConfig
from ragtrain.types import (
    MCQ,
    PromptType,
    SubjectDomain,
    GPT_MODEL,
    GPT_MODEL_MAX_TOKENS
)
from ragtrain.prompt_manager import PromptManager
from ragtrain.template_manager import TemplateManager
from ragtrain.embeddings import EmbeddingsManager

# Test fixtures and setup
TEST_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = TEST_DIR / "data" / "prompt_templates"

MAX_CHUNKS = 4  # Max chunks to return for this experiment


@pytest.fixture
def sample_mcq():
    return MCQ(
        id="q1",
        question="What is the main function of mitochondria in a cell?",
        answers=[
            "Store genetic material",
            "Produce energy through ATP synthesis",
            "Break down proteins",
            "Control cell division"
        ],
        correct_answer=1
    )


@pytest.fixture
def mock_embeddings_manager():
    manager = Mock(spec=EmbeddingsManager)
    # Default to returning biology domain
    manager.get_subject_domain.return_value = SubjectDomain.BIOLOGY
    return manager


@pytest.fixture
def mock_template_manager():
    manager = Mock(spec=TemplateManager)
    # Return a simple template that includes RAG chunks
    manager.get_template.return_value = """
    Here is the context:
    ${rag_chunks}

    QUESTION:
    ${question}

    CHOICES:
    ${formatted_choices}
    """
    return manager


@pytest.fixture
def prompt_manager(mock_template_manager, mock_embeddings_manager):
    return PromptManager(
        template_manager=mock_template_manager,
        embeddings_manager=mock_embeddings_manager
    )


@pytest.fixture
def rag_config():
    return PromptConfig(
        prompt_template_dir=TEMPLATE_DIR,
        versions={
            PromptType.RAG: PromptVersionConfig(version="1", enabled=True)
        }
    )


def test_rag_chunks_retrieval(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test successful retrieval of RAG chunks"""
    # Setup mock chunks
    mock_chunks = [
        "Mitochondria convert glucose into cellular energy through ATP synthesis",
        "DNA contains the genetic instructions for all living organisms.",
        "Photosynthesis allows plants to convert sunlight into chemical energy.",
        "Cell membranes regulate what enters and exits the cell.",
        "Enzymes speed up chemical reactions in biological systems.",
        "Ribosomes are the protein factories of cells.",
        "Neurons communicate through electrical and chemical signals.",
        "Chloroplasts give plants their green color and enable photosynthesis.",
        "The endoplasmic reticulum transports materials within cells.",
        "Antibodies help the immune system fight against pathogens.",
    ]

    mock_embeddings_manager.get_top_k_embeddings.return_value = mock_chunks[:MAX_CHUNKS]

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    # Verify chunks are in the prompt
    for idx, chunk in enumerate(mock_chunks):
        if idx < MAX_CHUNKS:
            assert chunk in rag_prompt
    assert "Here is another RAG chunk" in rag_prompt  # Verify separator


def test_rag_fallback_to_general(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test fallback to general domain when no biology chunks found"""
    # Setup mock to return no biology chunks but some general chunks
    mock_embeddings_manager.get_top_k_embeddings.side_effect = [
        [],  # No biology chunks
        ["General science concept: Energy production"]  # General chunks
    ]

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    # Verify general chunk is used
    assert "General science concept" in rag_prompt

    # Verify called with both domains
    calls = mock_embeddings_manager.get_top_k_embeddings.call_args_list
    assert calls[0][0][1] == SubjectDomain.BIOLOGY
    assert calls[1][0][1] == SubjectDomain.GENERAL


def test_rag_no_chunks_found(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test handling when no chunks are found in any domain"""
    # Setup mock to return no chunks for any domain
    mock_embeddings_manager.get_top_k_embeddings.return_value = []

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    assert "NO RAG CHUNKS FOUND" in rag_prompt


def test_rag_chunk_token_truncation(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test that RAG chunks are truncated to fit token limit"""
    # Create a long chunk that will need truncation
    long_chunk = "word " * 1000  # Will be way more tokens than allowed
    mock_embeddings_manager.get_top_k_embeddings.return_value = [long_chunk]

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    # Count tokens in the RAG portion
    encoder = tiktoken.encoding_for_model(GPT_MODEL)
    tokens = len(encoder.encode(rag_prompt))

    assert tokens <= GPT_MODEL_MAX_TOKENS, "Prompt exceeds token limit"


def test_rag_content_formatting(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test that RAG content is properly formatted in the prompt"""
    chunks = [
        "Chunk 1 content",
        "Chunk 2 content"
    ]
    mock_embeddings_manager.get_top_k_embeddings.return_value = chunks

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    # Verify chunk separator and order
    chunk_separator = "Here is another RAG chunk"
    chunk_positions = [rag_prompt.find(chunk) for chunk in chunks]
    separator_position = rag_prompt.find(chunk_separator)

    # First chunk should appear before separator
    assert chunk_positions[0] < separator_position
    # Second chunk should appear after separator
    assert chunk_positions[1] > separator_position


def test_rag_num_chunks_respected(prompt_manager, mock_embeddings_manager, sample_mcq, rag_config):
    """Test that the specified number of chunks is respected"""
    # Create more chunks than the default num_chunks (4)
    available_chunks = [f"Chunk {i}" for i in range(6)]
    mock_embeddings_manager.get_top_k_embeddings.return_value = available_chunks[:MAX_CHUNKS]

    prompts = prompt_manager.make_prompts(sample_mcq, rag_config)
    rag_prompt = prompts[PromptType.RAG]

    # Count occurrences of chunk separator
    separator_count = rag_prompt.count("Here is another RAG chunk")
    assert separator_count == 3  # For 4 chunks, there should be 3 separators
