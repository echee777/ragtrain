import pytest
from pathlib import Path
import yaml
from pydantic import ValidationError
from ragtrain.experiments import ExperimentManager, ExperimentConfig, PromptType, SubjectDomain


@pytest.fixture
def base_config_dict():
    """Basic valid configuration dictionary"""
    return {
        "version": "1.0",
        "experiment_id": "test_exp_001",
        "description": "Test experiment",
        "output_dir": "results/test_exp_001",
        "prompt_config": {
            "subject_domain": "biology",
            "prompt_template_dir": "templates/biology",
            "versions": {
                "cot": {
                    "version": "1",
                    "enabled": True
                },
                "few_shot": "1",  # Test shorthand notation
                "cot_few_shot": {
                    "enabled": False
                },
                "contrarian": {
                    "version": "1",
                    "enabled": True
                }
            }
        }
    }


@pytest.fixture
def setup_template_files(tmp_path):
    """Create template directory structure with sample templates"""
    templates_dir = tmp_path / "templates" / "biology"

    # Create template files
    for prompt_type in PromptType:
        template_dir = templates_dir / prompt_type.value
        template_dir.mkdir(parents=True)
        template_path = template_dir / "v1.txt"
        template_path.write_text(f"Template for {prompt_type.value}")

        # Add v2 for COT
        if prompt_type == PromptType.COT:
            (template_dir / "v2.txt").write_text("COT template v2")

    return templates_dir


@pytest.fixture
def experiment_manager(tmp_path, setup_template_files):
    """Create ExperimentManager with temporary directory structure"""
    return ExperimentManager(tmp_path)


def test_create_experiment(experiment_manager, base_config_dict):
    """Test creating a new experiment configuration"""
    config = ExperimentConfig.parse_obj(base_config_dict)
    path = experiment_manager.create_experiment(config)

    assert path.exists()
    assert path.name == f"{config.experiment_id}.yaml"

    # Load and verify saved config
    loaded_config = ExperimentConfig.parse_obj(yaml.safe_load(path.read_text()))
    assert loaded_config.experiment_id == config.experiment_id
    assert loaded_config.prompt_config.subject_domain == config.prompt_config.subject_domain


def test_load_experiment(experiment_manager, base_config_dict):
    """Test loading an existing experiment"""
    # Create experiment first
    config_path = experiment_manager.experiments_dir / "test_exp_001.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text(yaml.dump(base_config_dict))

    # Load experiment
    config = experiment_manager.load_experiment("test_exp_001")

    assert config.experiment_id == "test_exp_001"
    assert config.prompt_config.subject_domain == SubjectDomain.BIOLOGY
    assert config.get_prompt_version(PromptType.COT) == "1"


def test_load_nonexistent_experiment(experiment_manager):
    """Test loading a non-existent experiment"""
    with pytest.raises(FileNotFoundError):
        experiment_manager.load_experiment("nonexistent")


def test_invalid_config_format(experiment_manager, base_config_dict):
    """Test loading invalid configuration format"""
    # Create invalid config
    invalid_config = base_config_dict.copy()
    invalid_config["version"] = "2.0"  # Unsupported version

    config_path = experiment_manager.experiments_dir / "invalid_exp.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text(yaml.dump(invalid_config))

    with pytest.raises(ValidationError):
        experiment_manager.load_experiment("invalid_exp")


def test_missing_template(experiment_manager, base_config_dict):
    """Test validation of missing template files"""
    # Modify config to reference non-existent template
    config = base_config_dict.copy()
    config["prompt_config"]["versions"]["cot"]["version"] = "999"

    with pytest.raises(ValueError, match="Template not found"):
        experiment_manager.create_experiment(ExperimentConfig.parse_obj(config))


def test_list_experiments(experiment_manager, base_config_dict):
    """Test listing available experiments"""
    # Create multiple experiments
    experiments = {
        "exp1": base_config_dict.copy(),
        "exp2": base_config_dict.copy()
    }

    experiments["exp1"]["experiment_id"] = "exp1"
    experiments["exp2"]["experiment_id"] = "exp2"

    for exp_id, config in experiments.items():
        config_path = experiment_manager.experiments_dir / f"{exp_id}.yaml"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(yaml.dump(config))

    # List experiments
    available_experiments = experiment_manager.list_experiments()

    assert len(available_experiments) == 2
    assert "exp1" in available_experiments
    assert "exp2" in available_experiments
    assert all(isinstance(config, ExperimentConfig)
               for config in available_experiments.values())


def test_duplicate_experiment(experiment_manager, base_config_dict):
    """Test creating duplicate experiment"""
    config = ExperimentConfig.parse_obj(base_config_dict)

    # Create first experiment
    experiment_manager.create_experiment(config)

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        experiment_manager.create_experiment(config)


def test_get_template_content(experiment_manager, base_config_dict):
    """Test retrieving template content"""
    config = ExperimentConfig.parse_obj(base_config_dict)
    experiment_manager.create_experiment(config)

    # Get template content
    content = experiment_manager.get_template_content(config, PromptType.COT)
    assert f"Template for {PromptType.COT.value}" in content


def test_get_template_content_disabled_prompt(experiment_manager, base_config_dict):
    """Test retrieving template content for disabled prompt type"""
    config = ExperimentConfig.parse_obj(base_config_dict)
    experiment_manager.create_experiment(config)

    with pytest.raises(ValueError, match="not enabled"):
        experiment_manager.get_template_content(config, PromptType.COT_FEW_SHOT)


def test_relative_paths(experiment_manager, base_config_dict):
    """Test handling of relative paths in config"""
    # Create experiment with relative paths
    config = ExperimentConfig.parse_obj(base_config_dict)
    path = experiment_manager.create_experiment(config)

    # Load and verify paths are resolved
    loaded_config = experiment_manager.load_experiment(config.experiment_id)
    assert loaded_config.output_dir.is_absolute()
    assert loaded_config.prompt_config.prompt_template_dir.is_absolute()