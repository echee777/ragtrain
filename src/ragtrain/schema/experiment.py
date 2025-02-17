from typing import Dict, Optional
from pathlib import Path
from pydantic import BaseModel, model_validator, Field, ConfigDict
from ragtrain.types import PromptType, SubjectDomain


class PromptVersionConfig(BaseModel):
    """Configuration for a specific prompt version"""
    enabled: bool
    version: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode='after')
    def validate_version(self) -> 'PromptVersionConfig':
        """Validate version is provided when enabled"""
        if self.enabled and not self.version:
            raise ValueError("Version is required when enabled")
        return self


class PromptConfig(BaseModel):
    """Configuration for prompt generation"""
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
                    version="1",
                    enabled=False
                )

        # Ensure at least one prompt type is enabled
        if not any(v.enabled for v in self.versions.values()):
            raise ValueError("At least one prompt type must be enabled")
        return self


class ExperimentConfig(BaseModel):
    """Configuration for running an experiment"""
    name: str
    description: Optional[str] = None
    prompt_config: PromptConfig
    rag_chunk_count: int = Field(default=3, gt=0)

    model_config = ConfigDict(extra="forbid")