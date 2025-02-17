import pytest
from pathlib import Path
import json
from typing import Dict, Any
from ragtrain.schema.experiment import ExperimentConfig, PromptConfig, PromptVersionConfig
from ragtrain.types import PromptType, SubjectDomain
from enum import Enum


class ConfigEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Path objects and Enum values"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (Path, Enum)):
            return str(obj)
        return super().default(obj)


@pytest.fixture
def base_config_dict() -> Dict:
    """Basic valid experiment configuration as a dictionary"""
    return {
        "name": "test_experiment",
        "prompt_config": {
            "subject_domain": "biology",
            "prompt_template_dir": "/tmp/templates",
            "versions": {
                "cot": {
                    "subject_domain": "biology",
                    "version": "1",
                    "enabled": True,
                    "prompt_types": ["cot"]
                },
                # Add a disabled version to ensure we always have one enabled type
                "few_shot": {
                    "subject_domain": "biology",
                    "enabled": False,
                    "prompt_types": []
                }
            }
        },
        "rag_chunk_count": 3
    }


@pytest.fixture
def experiment_json(tmp_path, base_config_dict):
    """Creates a temporary JSON file with experiment configuration"""
    json_path = tmp_path / "experiment.json"
    with open(json_path, 'w') as f:
        json.dump(base_config_dict, f)
    return json_path


def test_load_experiment_config(base_config_dict):
    """Test loading experiment config from dictionary"""
    config = ExperimentConfig.model_validate(base_config_dict)
    assert config.name == "test_experiment"
    assert config.prompt_config.subject_domain == SubjectDomain.BIOLOGY
    assert config.rag_chunk_count == 3

    # Check version config
    cot_version = config.prompt_config.versions[PromptType.COT]
    assert cot_version.enabled
    assert cot_version.version == "1"
    assert PromptType.COT in cot_version.prompt_types


def test_load_from_json(experiment_json):
    """Test loading experiment config from JSON file"""
    with open(experiment_json) as f:
        data = json.load(f)
    config = ExperimentConfig.model_validate(data)
    assert config.name == "test_experiment"
    assert isinstance(config.prompt_config.prompt_template_dir, Path)


def test_invalid_subject_domain(base_config_dict):
    """Test validation fails with mismatched subject domains"""
    base_config_dict["prompt_config"]["versions"]["cot"]["subject_domain"] = "general"
    with pytest.raises(ValueError, match="Version config subject domain.*does not match"):
        ExperimentConfig.model_validate(base_config_dict)


def test_missing_version_enabled(base_config_dict):
    """Test validation fails when version is missing for enabled config"""
    del base_config_dict["prompt_config"]["versions"]["cot"]["version"]
    with pytest.raises(ValueError, match="Version is required when enabled"):
        ExperimentConfig.model_validate(base_config_dict)


def test_disabled_no_version(base_config_dict):
    """Test validation passes for disabled config without version"""
    # Keep the enabled COT config to satisfy the "at least one enabled" requirement
    # Add a new disabled config without version
    base_config_dict["prompt_config"]["versions"]["contrarian"] = {
        "subject_domain": "biology",
        "enabled": False,
        "prompt_types": []
    }
    config = ExperimentConfig.model_validate(base_config_dict)
    assert not config.prompt_config.versions[PromptType.CONTRARIAN].enabled
    assert config.prompt_config.versions[PromptType.CONTRARIAN].version is None


def test_auto_disabled_versions(base_config_dict):
    """Test other prompt types are auto-created as disabled"""
    config = ExperimentConfig.model_validate(base_config_dict)
    # COT should be enabled from config
    assert config.prompt_config.versions[PromptType.COT].enabled
    # Auto-created types should be disabled
    assert not config.prompt_config.versions[PromptType.CONTRARIAN].enabled


def test_all_versions_disabled(base_config_dict):
    """Test validation fails when all versions are disabled"""
    base_config_dict["prompt_config"]["versions"]["cot"]["enabled"] = False
    base_config_dict["prompt_config"]["versions"]["few_shot"]["enabled"] = False
    with pytest.raises(ValueError, match="At least one prompt type must be enabled"):
        ExperimentConfig.model_validate(base_config_dict)


def test_save_and_load_config(tmp_path, base_config_dict):
    """Test config can be saved and loaded while preserving all properties"""
    # Create initial config
    config = ExperimentConfig.model_validate(base_config_dict)

    # Convert model to dict and handle enums
    config_dict = config.model_dump()
    versions = config_dict["prompt_config"]["versions"]
    config_dict["prompt_config"]["versions"] = {
        k.value if isinstance(k, PromptType) else k: v
        for k, v in versions.items()
    }

    # Save to file
    config_path = tmp_path / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, cls=ConfigEncoder)

    # Verify JSON is valid by reading it
    with open(config_path) as f:
        raw_json = f.read()
        # Ensure it's valid JSON
        saved_data = json.loads(raw_json)

    # Verify enum values are correctly serialized
    assert "cot" in saved_data["prompt_config"]["versions"]
    assert saved_data["prompt_config"]["versions"]["cot"]["subject_domain"] == "biology"
    assert saved_data["prompt_config"]["versions"]["cot"]["prompt_types"] == ["cot"]

    # Load back into config object
    loaded_config = ExperimentConfig.model_validate(saved_data)

    # Verify core properties
    assert loaded_config.name == config.name
    assert loaded_config.rag_chunk_count == config.rag_chunk_count
    assert loaded_config.prompt_config.subject_domain == config.prompt_config.subject_domain

    # Verify version configs
    cot_version = loaded_config.prompt_config.versions[PromptType.COT]
    assert cot_version.enabled
    assert cot_version.version == "1"
    assert cot_version.prompt_types == [PromptType.COT]
    assert cot_version.subject_domain == SubjectDomain.BIOLOGY

    # Verify disabled configs
    few_shot_version = loaded_config.prompt_config.versions[PromptType.FEW_SHOT]
    assert not few_shot_version.enabled
    assert len(few_shot_version.prompt_types) == 0