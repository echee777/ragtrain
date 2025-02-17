import pytest
from pathlib import Path
import os
from typing import Dict

from ragtrain.schema.experiment import PromptVersionConfig, PromptConfig
from ragtrain.types import (
    MCQ,
    PromptType,
    SubjectDomain
)
from ragtrain.prompt_manager import PromptManager, TemplateManager
from ragtrain.embeddings import (
    EmbeddingsManager,
    BiobertEmbedder,
    GeneralEmbedder,
    ChromaVectorStore
)

# Get the directory containing this test file
TEST_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = TEST_DIR / "data" / "prompt_templates"


@pytest.fixture
def vector_stores(monkeypatch):
    monkeypatch.setenv("ALLOW_RESET", "TRUE")  # allow chroma db resets
    biology_store = ChromaVectorStore(collection_name="biology", get_or_create=True)
    general_store = ChromaVectorStore(collection_name="biology", get_or_create=True)
    yield {
        "biology": biology_store,
        "general": general_store,
    }
    biology_store.clear()
    general_store.reset()


@pytest.fixture
def embedders():
    """Setup and teardown embedders"""
    biology_embedder = BiobertEmbedder()
    general_embedder = GeneralEmbedder()

    # Start embedders
    biology_embedder.start()
    general_embedder.start()

    yield {
        "biology": biology_embedder,
        "general": general_embedder
    }

    # Stop embedders
    biology_embedder.stop()
    general_embedder.stop()


@pytest.fixture
def embeddings_manager(vector_stores, embedders):
    """Setup EmbeddingsManager with registered embedders"""
    manager = EmbeddingsManager()
    manager.register_embedder(SubjectDomain.BIOLOGY, embedders["biology"], vector_stores["biology"])
    manager.register_embedder(SubjectDomain.GENERAL, embedders["general"], vector_stores["general"])
    return manager



@pytest.fixture
def template_manager():
    """Setup TemplateManager"""
    return TemplateManager(base_path=str(TEMPLATE_DIR))


@pytest.fixture
def prompt_manager(template_manager, embeddings_manager):
    """Setup PromptManager with dependencies"""
    manager = PromptManager(
        template_manager=template_manager,
        embeddings_manager=embeddings_manager
    )
    return manager


@pytest.fixture
def sample_mcq():
    """Create a sample MCQ for testing"""
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
def sample_config():
    """Create a sample PromptConfig with all types enabled"""
    return PromptConfig(
        prompt_template_dir=TEMPLATE_DIR,
        versions={
            PromptType.COT: PromptVersionConfig(version="1", enabled=True),
            PromptType.FEW_SHOT: PromptVersionConfig(version="1", enabled=True),
            PromptType.CONTRARIAN: PromptVersionConfig(version="1", enabled=True),
            PromptType.RAG: PromptVersionConfig(version="1", enabled=True)
        }
    )


def test_make_prompts_returns_enabled_types(prompt_manager, sample_mcq, sample_config):
    """Test that make_prompts returns only enabled prompt types"""
    # Disable some prompt types
    sample_config.versions[PromptType.CONTRARIAN].enabled = False
    sample_config.versions[PromptType.RAG].enabled = False
    prompts = prompt_manager.make_prompts(sample_mcq, sample_config)

    # Should only contain enabled types
    assert set(prompts.keys()) == {PromptType.COT, PromptType.FEW_SHOT}


def test_make_prompts_with_rag(prompt_manager, sample_mcq, sample_config):
    """Test RAG prompt generation with embeddings"""
    # Ensure RAG is enabled
    sample_config.versions[PromptType.RAG].enabled = True

    prompts = prompt_manager.make_prompts(sample_mcq, sample_config)
    rag_prompt = prompts[PromptType.RAG]

    # Check prompt contains the key template sections in order
    assert rag_prompt.startswith("I'll help you answer this multiple choice question")
    assert "Here are some relevant excerpts from a related knowledge base" in rag_prompt
    assert "CONTEXT:" in rag_prompt
    assert "Now, let's use this information to answer the following question:" in rag_prompt

    # The question should appear after the context section
    context_idx = rag_prompt.index("CONTEXT:")
    question_idx = rag_prompt.index("QUESTION:")
    assert context_idx < question_idx, "Question should appear after context"

    choices_section = "ANSWER CHOICES:\n" + "\n".join(
        f"{i + 1}. {ans}" for i, ans in enumerate(sample_mcq.answers)
    )
    assert choices_section in rag_prompt


def test_make_prompts_with_disabled_types(prompt_manager, sample_mcq, sample_config):
    """Test that disabled prompt types are excluded"""
    # Disable all except COT
    for prompt_type in PromptType:
        sample_config.versions[prompt_type].enabled = False
    sample_config.versions[PromptType.COT].enabled = True

    prompts = prompt_manager.make_prompts(sample_mcq, sample_config)

    assert len(prompts) == 1
    assert PromptType.COT in prompts
    assert PromptType.RAG not in prompts
    assert PromptType.FEW_SHOT not in prompts
    assert PromptType.CONTRARIAN not in prompts


def test_make_prompts_with_biology_domain(prompt_manager, sample_mcq, sample_config):
    """Test prompts with biology domain specifics"""
    prompts = prompt_manager.make_prompts(sample_mcq, sample_config)

    # Check biology-specific content in few-shot prompt
    few_shot_prompt = prompts[PromptType.FEW_SHOT]
    assert "cellular respiration" in few_shot_prompt
    assert "pyruvate molecules" in few_shot_prompt


def test_template_directory_exists():
    """Test that the template directory exists"""
    assert TEMPLATE_DIR.exists(), f"Template directory not found at: {TEMPLATE_DIR}"
    assert TEMPLATE_DIR.is_dir(), f"Template path is not a directory: {TEMPLATE_DIR}"


def test_required_templates_exist():
    """Test that all required template files exist"""
    required_templates = [
        ("general", "contrarian", "v1"),
        ("general", "few_shot", "v1"),
        ("general", "cot", "v1"),
        ("general", "rag", "v1"),
        ("biology", "few_shot", "v1")
    ]

    for subject, prompt_type, version in required_templates:
        template_path = TEMPLATE_DIR / subject / prompt_type / f"{version}.txt"
        assert template_path.exists(), f"Required template not found: {template_path}"


def test_all_prompt_types_disabled_raises_error():
    """Test that having all prompt types disabled raises an error"""
    with pytest.raises(ValueError, match="At least one prompt type must be enabled"):
        PromptConfig(
            prompt_template_dir=TEMPLATE_DIR,
            versions={
                PromptType.COT: PromptVersionConfig(version="1", enabled=False),
                PromptType.FEW_SHOT: PromptVersionConfig(version="1", enabled=False),
                PromptType.CONTRARIAN: PromptVersionConfig(version="1", enabled=False),
                PromptType.RAG: PromptVersionConfig(version="1", enabled=False)
            }
        )


def test_invalid_template_version(prompt_manager, sample_mcq, sample_config):
    """Test handling of invalid template versions"""
    # Set an invalid version
    sample_config.versions[PromptType.COT].version = "999"

    with pytest.raises(FileNotFoundError):
        prompt_manager.make_prompts(sample_mcq, sample_config)