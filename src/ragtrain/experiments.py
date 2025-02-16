from pathlib import Path
import yaml
from typing import Dict, Optional
import logging
from pydantic import ValidationError, BaseModel, Field, root_validator, validator
from typing import Dict, Optional
from pathlib import Path
from ragtrain.embeddings import SubjectDomain
from ragtrain.types import PromptType


logger = logging.getLogger(__name__)


class PromptVersionConfig(BaseModel):
    """Configuration for a specific prompt type"""
    enabled: bool = True
    version: Optional[str] = None

    @root_validator
    def validate_version_if_enabled(cls, values):
        """Ensure version is provided if prompt is enabled"""
        enabled = values.get('enabled')
        version = values.get('version')
        if enabled and not version:
            raise ValueError("Version must be provided when prompt is enabled")
        return values

    class Config:
        """Pydantic model configuration"""
        extra = "forbid"  # Forbid extra attributes


class PromptConfig(BaseModel):
    """Configuration for prompt generation"""
    subject_domain: SubjectDomain
    prompt_template_dir: Path
    versions: Dict[PromptType, PromptVersionConfig]

    class Config:
        """Pydantic model configuration"""
        extra = "forbid"

    @validator('versions')
    def validate_versions(cls, v):
        """Ensure all prompt types have a version configuration"""
        # Check that all prompt types are covered
        for prompt_type in PromptType:
            if prompt_type not in v:
                v[prompt_type] = PromptVersionConfig(enabled=False)
        return v


class ExperimentConfig(BaseModel):
    """Configuration for a MCQ experiment"""
    version: str = Field(..., description="Config format version")
    experiment_id: str = Field(..., pattern="^[a-zA-Z0-9_]+$",
                               description="Unique identifier for experiment")
    description: str = Field(default="", description="Experiment description")
    prompt_config: PromptConfig
    output_dir: Path = Field(..., description="Directory for experiment outputs")
    num_attempts: int = Field(default=1, gt=0,
                              description="Number of attempts per question")

    class Config:
        """Pydantic model configuration"""
        extra = "forbid"  # Forbid extra attributes
        arbitrary_types_allowed = True  # Allow Path objects

    @validator('version')
    def validate_version(cls, v):
        """Validate config version"""
        if v != "1.0":  # Current supported version
            raise ValueError(f"Unsupported config version: {v}. Only 1.0 is supported.")
        return v

    @validator('experiment_id')
    def validate_experiment_id(cls, v):
        """Additional validation for experiment_id"""
        if len(v) < 3:
            raise ValueError("experiment_id must be at least 3 characters long")
        return v

    @root_validator
    def validate_paths(cls, values):
        """Validate path configurations"""
        if 'output_dir' in values:
            output_dir = values['output_dir']
            if isinstance(output_dir, str):
                values['output_dir'] = Path(output_dir)
        return values

    def get_enabled_prompt_types(self) -> list[PromptType]:
        """Get list of enabled prompt types"""
        return [
            pt for pt, vc in self.prompt_config.versions.items()
            if vc.enabled
        ]

    def get_prompt_version(self, prompt_type: PromptType) -> Optional[str]:
        """Get version for a prompt type if enabled"""
        version_config = self.prompt_config.versions.get(prompt_type)
        if version_config and version_config.enabled:
            return version_config.version
        return None


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
