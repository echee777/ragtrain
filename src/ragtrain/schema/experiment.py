from pydantic import ValidationError, BaseModel, model_validator, validator, Field

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
