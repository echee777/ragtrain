from pathlib import Path
import yaml
from typing import Dict, Optional
import logging
from pydantic import ValidationError, BaseModel, model_validator, validator, Field


logger = logging.getLogger(__name__)

from typing import Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, model_validator, Field, ConfigDict
from ragtrain.types import PromptType, SubjectDomain


class PromptVersionConfig(BaseModel):
    """Configuration for a specific prompt version"""
    subject_domain: SubjectDomain
    enabled: bool
    version: Optional[str] = None
    prompt_types: List[PromptType] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode='after')
    def validate_prompt_types(self) -> 'PromptVersionConfig':
        """Validate that prompt types are valid for this version
        and version is provided when enabled"""
        if self.enabled:
            if not self.prompt_types:
                raise ValueError("At least one prompt type must be specified")
            if not self.version:
                raise ValueError("Version is required when enabled")
        return self


class PromptConfig(BaseModel):
    """Configuration for prompt generation"""
    subject_domain: SubjectDomain
    prompt_template_dir: Path
    versions: Dict[PromptType, PromptVersionConfig]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode='after')
    def validate_config(self) -> 'PromptConfig':
        """Validate overall prompt configuration"""
        # Create disabled configs for any missing prompt types
        for prompt_type in PromptType:
            if prompt_type not in self.versions:
                self.versions[prompt_type] = PromptVersionConfig(
                    subject_domain=self.subject_domain,
                    version="1",
                    enabled=False,
                    prompt_types=[]
                )
            elif self.versions[prompt_type].enabled:
                # Validate subject domain matches for enabled configs
                if self.versions[prompt_type].subject_domain != self.subject_domain:
                    raise ValueError(
                        f"Version config subject domain {self.versions[prompt_type].subject_domain} "
                        f"does not match main config domain {self.subject_domain}"
                    )
        return self


class ExperimentConfig(BaseModel):
    """Configuration for running an experiment"""
    name: str
    description: Optional[str] = None
    prompt_config: PromptConfig
    rag_chunk_count: int = Field(default=3, gt=0)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode='after')
    def validate_config(self) -> 'ExperimentConfig':
        """Validate that at least one prompt type is enabled"""
        if not any(v.enabled for v in self.prompt_config.versions.values()):
            raise ValueError("At least one prompt type must be enabled")
        return self

# Example usage:
"""
config = ExperimentConfig(
    name="biology_v1_test",
    description="Testing biology prompts with v1 templates",
    prompt_config=PromptVersionConfig(
        subject_domain="biology",
        version="1",
        prompt_types=[PromptType.COT, PromptType.FEW_SHOT]
    ),
    rag_chunk_count=3
)
"""

class ExperimentManager:
    """Manages experiment configurations"""

    def __init__(self, base_dir: Path):
        """Initialize experiment manager

        Args:
            base_dir: Base directory containing experiments and templates
        """
        self.base_dir = Path(base_dir)
        self.experiments_dir = self.base_dir / "experiments"
        self.templates_dir = self.base_dir / "templates"

        # Ensure directories exist
        self.experiments_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)

    def load_experiment(self, experiment_id: str) -> ExperimentConfig:
        """Load experiment configuration by ID

        Args:
            experiment_id: Unique identifier for experiment

        Returns:
            Loaded and validated experiment configuration

        Raises:
            FileNotFoundError: If experiment config not found
            ValidationError: If config is invalid
        """
        config_path = self.experiments_dir / f"{experiment_id}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Experiment config not found: {config_path}")

        # Load YAML and convert to ExperimentConfig
        with open(config_path, 'r') as f:
            try:
                raw_config = yaml.safe_load(f)
                config = ExperimentConfig.parse_obj(raw_config)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}")
            except ValidationError as e:
                logger.error(f"Validation failed for {config_path}")
                raise

        # Resolve and validate paths
        self._validate_paths(config)

        return config

    def _validate_paths(self, config: ExperimentConfig):
        """Validate and resolve all paths in config

        Args:
            config: Experiment configuration

        Raises:
            ValueError: If any required paths are invalid
        """
        # Validate template directory
        template_dir = self.templates_dir / config.prompt_config.prompt_template_dir
        if not template_dir.exists():
            raise ValueError(f"Template directory not found: {template_dir}")

        # Validate templates exist for enabled prompt types
        for prompt_type, version_config in config.prompt_config.versions.items():
            if version_config.enabled and version_config.version:
                template_path = (template_dir /
                                 config.prompt_config.subject_domain.value /
                                 prompt_type.value /
                                 f"v{version_config.version}.txt")
                if not template_path.exists():
                    raise ValueError(
                        f"Template not found for {prompt_type.value} "
                        f"version {version_config.version}: {template_path}"
                    )

        # Create output directory if it doesn't exist
        output_dir = self.base_dir / config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Update paths to be absolute
        config.output_dir = output_dir
        config.prompt_config.prompt_template_dir = template_dir

    def list_experiments(self) -> Dict[str, ExperimentConfig]:
        """List available experiments

        Returns:
            Dict mapping experiment ID to loaded config
        """
        experiments = {}
        for config_file in self.experiments_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r') as f:
                    raw_config = yaml.safe_load(f)
                config = ExperimentConfig.parse_obj(raw_config)
                self._validate_paths(config)
                experiments[config.experiment_id] = config
            except Exception as e:
                logger.warning(f"Error loading {config_file}: {str(e)}")
                continue
        return experiments

    def create_experiment(self, config: ExperimentConfig) -> Path:
        """Save new experiment configuration

        Args:
            config: Experiment configuration to save

        Returns:
            Path to saved config file

        Raises:
            ValueError: If experiment already exists
        """
        # Validate paths before saving
        self._validate_paths(config)

        output_path = self.experiments_dir / f"{config.experiment_id}.yaml"
        if output_path.exists():
            raise ValueError(f"Experiment {config.experiment_id} already exists")

        # Convert config to dict for YAML
        # Use Pydantic's dict() method to handle all nested objects
        config_dict = config.dict(exclude_none=True)

        # Convert paths to strings relative to base_dir
        config_dict['output_dir'] = str(Path(config_dict['output_dir']).relative_to(self.base_dir))
        config_dict['prompt_config']['prompt_template_dir'] = str(
            Path(config_dict['prompt_config']['prompt_template_dir']).relative_to(self.templates_dir)
        )

        # Save to YAML
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)

        return output_path

    def get_template_content(self, config: ExperimentConfig, prompt_type: PromptType) -> str:
        """Get content of a specific template

        Args:
            config: Experiment configuration
            prompt_type: Type of prompt to get

        Returns:
            Template content

        Raises:
            ValueError: If template not found or prompt type not enabled
        """
        version_config = config.prompt_config.versions.get(prompt_type)
        if not version_config or not version_config.enabled:
            raise ValueError(f"Prompt type {prompt_type} not enabled in config")

        template_path = (self.templates_dir /
                         config.prompt_config.prompt_template_dir /
                         config.prompt_config.subject_domain.value /
                         prompt_type.value /
                         f"v{version_config.version}.txt")

        if not template_path.exists():
            raise ValueError(f"Template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()
