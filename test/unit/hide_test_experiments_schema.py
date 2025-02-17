import pytest
from pathlib import Path
from pydantic import ValidationError
from ragtrain.experiments import ExperimentConfig, PromptConfig, PromptVersionConfig
from ragtrain.types import PromptType, SubjectDomain


# Fixtures
@pytest.fixture
def valid_version_config():
    """Fixture providing a valid version configuration"""
    return PromptVersionConfig(
        subject_domain=SubjectDomain.BIOLOGY,
        version="1",
        enabled=True,
        prompt_types=[PromptType.COT]
    )


@pytest.fixture
def valid_prompt_config(valid_version_config, tmp_path):
    """Fixture providing a valid prompt configuration"""
    return PromptConfig(
        subject_domain=SubjectDomain.BIOLOGY,
        prompt_template_dir=tmp_path,
        versions={
            PromptType.COT: valid_version_config
        }
    )


# Version Config Tests
def test_version_config_enabled_requires_version():
    """Test that enabled config requires version"""
    with pytest.raises(ValueError, match="Version is required when enabled"):
        PromptVersionConfig(
            subject_domain=SubjectDomain.BIOLOGY,
            enabled=True,
            prompt_types=[PromptType.COT]
        )


def test_version_config_disabled_no_version():
    """Test that disabled config doesn't require version"""
    config = PromptVersionConfig(
        subject_domain=SubjectDomain.BIOLOGY,
        enabled=False
    )
    assert not config.enabled
    assert config.version is None
    assert len(config.prompt_types) == 0


def test_version_config_enabled_valid():
    """Test valid enabled config with version"""
    config = PromptVersionConfig(
        subject_domain=SubjectDomain.BIOLOGY,
        enabled=True,
        version="1",
        prompt_types=[PromptType.COT]
    )
    assert config.enabled
    assert config.version == "1"
    assert len(config.prompt_types) == 1


def test_version_config_no_types():
    """Test enabled config requires prompt types"""
    with pytest.raises(ValueError, match="At least one prompt type must be specified"):
        PromptVersionConfig(
            subject_domain=SubjectDomain.BIOLOGY,
            enabled=True,
            version="1",
            prompt_types=[]  # Invalid when enabled
        )


# Prompt Config Tests
def test_prompt_config_auto_disabled(valid_version_config, tmp_path):
    """Test prompt config auto-creates disabled configs"""
    config = PromptConfig(
        subject_domain=SubjectDomain.BIOLOGY,
        prompt_template_dir=tmp_path,
        versions={
            PromptType.COT: valid_version_config
        }
    )
    # Should have configs for all prompt types
    assert len(config.versions) == len(PromptType)
    # Other configs should be disabled
    assert not config.versions[PromptType.FEW_SHOT].enabled
    assert not config.versions[PromptType.CONTRARIAN].enabled


def test_prompt_config_domain_mismatch(tmp_path):
    """Test validation fails when domains don't match"""
    with pytest.raises(ValueError, match="Version config subject domain.*does not match"):
        PromptConfig(
            subject_domain=SubjectDomain.BIOLOGY,
            prompt_template_dir=tmp_path,
            versions={
                PromptType.COT: PromptVersionConfig(
                    subject_domain=SubjectDomain.GENERAL,
                    version="1",
                    enabled=True,
                    prompt_types=[PromptType.COT]
                )
            }
        )


# Experiment Config Tests
def test_experiment_config_minimal(valid_prompt_config):
    """Test creating config with minimal required fields"""
    config = ExperimentConfig(
        name="test_experiment",
        prompt_config=valid_prompt_config
    )
    assert config.name == "test_experiment"
    assert config.description is None
    assert config.rag_chunk_count == 3  # Default value


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