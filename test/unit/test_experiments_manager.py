import pytest
from pathlib import Path
import json
from enum import Enum
from typing import Any
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


class ConfigEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Path objects and Enum values"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (Path, Enum)):
            return str(obj)
        return super().default(obj)


def test_experiment_config_serialization(tmp_path, valid_experiment_config):
    """Test that config can be properly serialized to JSON and back"""
    # Convert to dict and handle enums
    config_dict = valid_experiment_config.model_dump()
    versions = config_dict["prompt_config"]["versions"]
    config_dict["prompt_config"]["versions"] = {
        k.value if isinstance(k, PromptType) else k: v
        for k, v in versions.items()
    }

    # Save to JSON string using custom encoder
    config_json = json.dumps(config_dict, cls=ConfigEncoder)

    # Verify JSON structure
    saved_data = json.loads(config_json)
    assert "cot" in saved_data["prompt_config"]["versions"]
    assert saved_data["prompt_config"]["versions"]["cot"]["enabled"]
    assert saved_data["prompt_config"]["versions"]["cot"]["version"] == "1"

    # Load back into config object
    loaded_config = ExperimentConfig.model_validate(saved_data)

    # Verify core properties
    assert loaded_config.name == valid_experiment_config.name
    assert loaded_config.rag_chunk_count == valid_experiment_config.rag_chunk_count

    # Verify version configs
    cot_version = loaded_config.prompt_config.versions[PromptType.COT]
    assert cot_version.enabled
    assert cot_version.version == "1"

    # Verify disabled configs
    few_shot_version = loaded_config.prompt_config.versions[PromptType.FEW_SHOT]
    assert not few_shot_version.enabled