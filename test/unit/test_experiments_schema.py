import pytest
from pathlib import Path
from pydantic import ValidationError
from ragtrain.schema.experiment import ExperimentConfig, PromptConfig, PromptVersionConfig
from ragtrain.types import PromptType


@pytest.fixture
def valid_prompt_config(tmp_path):
    """Fixture providing a valid prompt configuration"""
    return PromptConfig(
        prompt_template_dir=tmp_path,
        versions={
            PromptType.COT: PromptVersionConfig(
                version="1",
                enabled=True
            )
        }
    )


@pytest.fixture
def valid_experiment_config(valid_prompt_config):
    """Fixture providing a valid experiment configuration"""
    return ExperimentConfig(
        name="test_experiment",
        prompt_config=valid_prompt_config,
        rag_chunk_count=3
    )


def test_prompt_version_enabled_requires_version():
    """Test that enabled config requires version"""
    with pytest.raises(ValueError, match="Version is required when enabled"):
        PromptVersionConfig(
            enabled=True,
            version=None
        )


def test_prompt_version_disabled_no_version():
    """Test that disabled config doesn't require version"""
    config = PromptVersionConfig(
        enabled=False
    )
    assert not config.enabled
    assert config.version is None


def test_prompt_config_auto_disabled(valid_prompt_config):
    """Test prompt config auto-creates disabled configs"""
    assert len(valid_prompt_config.versions) == len(PromptType)
    assert valid_prompt_config.versions[PromptType.COT].enabled
    assert not valid_prompt_config.versions[PromptType.FEW_SHOT].enabled


def test_experiment_config_minimal(valid_prompt_config):
    """Test creating config with minimal required fields"""
    config = ExperimentConfig(
        name="test_experiment",
        prompt_config=valid_prompt_config
    )
    assert config.name == "test_experiment"
    assert config.description is None
    assert config.rag_chunk_count == 3


def test_experiment_config_all_disabled(valid_prompt_config):
    """Test validation fails when no prompt types are enabled"""
    # Disable all version configs
    for version in valid_prompt_config.versions.values():
        version.enabled = False

    with pytest.raises(ValueError, match="At least one prompt type must be enabled"):
        ExperimentConfig(
            name="test_experiment",
            prompt_config=valid_prompt_config
        )


def test_experiment_config_invalid_chunks(valid_prompt_config):
    """Test validation of rag chunk count"""
    with pytest.raises(ValidationError) as exc_info:
        ExperimentConfig(
            name="test_experiment",
            prompt_config=valid_prompt_config,
            rag_chunk_count=0
        )
    assert "Input should be greater than 0" in str(exc_info.value)