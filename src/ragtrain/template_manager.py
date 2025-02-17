from ragtrain.types import PromptType, SubjectDomain
from pathlib import Path
from typing import Dict, List


class TemplateManager:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._validate_general_templates()

    def _validate_general_templates(self):
        """Validate that all required general templates exist"""
        for template_type in PromptType:
            general_path = self.base_path / SubjectDomain.GENERAL / template_type.value / "v1.txt"
            if not general_path.exists():
                raise FileNotFoundError(
                    f"Required general template missing: {general_path}. "
                    "General templates must be present for fallback functionality."
                )

    def get_template(self, subject: str, template_type: PromptType, version: str) -> str:
        """Get template content with fallback to general templates

        Args:
            subject: Subject domain (e.g. "biology")
            template_type: PromptType enum value
            version: Version string (e.g. "1")

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template doesn't exist and subject isn't valid for fallback
        """
        # For GENERAL domain, only look in general templates
        if subject.lower() == SubjectDomain.GENERAL:
            return self._get_general_template(template_type, version)

        # Check if subject directory exists
        subject_dir = self.base_path / subject.lower()
        if not subject_dir.exists():
            raise FileNotFoundError(f"Subject directory not found: {subject}")

        # For known subjects, try specific template then fallback
        if subject.lower() in [d.lower() for d in [SubjectDomain.BIOLOGY]]:
            try:
                return self._get_template_content(subject, template_type, version)
            except FileNotFoundError:
                return self._get_general_template(template_type, version)
        else:
            # For unknown subjects, don't fallback
            return self._get_template_content(subject, template_type, version)

    def _get_general_template(self, template_type: PromptType, version: str) -> str:
        """Get content of a general template"""
        template_path = (self.base_path / SubjectDomain.GENERAL /
                         template_type.value / f"v{version}.txt")
        if not template_path.exists():
            raise FileNotFoundError(f"General template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()

    def _get_template_content(self, subject: str, template_type: PromptType, version: str) -> str:
        """Get content of a specific template file"""
        template_path = self.base_path / subject.lower() / template_type.value / f"v{version}.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r') as f:
            return f.read()

    def list_templates(self, subject: str = None) -> Dict[str, Dict[PromptType, List[str]]]:
        """List available templates including fallbacks

        Args:
            subject: Optional subject to filter by

        Returns:
            Dict mapping subject -> PromptType -> list of versions
        """
        result = {}

        if subject:
            subject = subject.lower()
            result[subject] = {}

            # For known subjects, add both specific and fallback templates
            if subject in [d.lower() for d in [SubjectDomain.BIOLOGY]]:
                # Get general templates for fallbacks
                general_templates = {}
                general_dir = self.base_path / SubjectDomain.GENERAL
                if general_dir.exists():
                    for prompt_type in PromptType:
                        type_dir = general_dir / prompt_type.value
                        if type_dir.exists():
                            versions = [p.stem.replace('v', '') for p in type_dir.glob('v*.txt')]
                            if versions:
                                general_templates[prompt_type] = versions

                # Add subject-specific templates
                subject_dir = self.base_path / subject
                if subject_dir.exists():
                    for prompt_type in PromptType:
                        type_dir = subject_dir / prompt_type.value
                        specific_versions = []
                        if type_dir.exists():
                            specific_versions = [p.stem.replace('v', '') for p in type_dir.glob('v*.txt')]

                        # Add both specific and fallback versions
                        if prompt_type in general_templates or specific_versions:
                            result[subject][prompt_type] = specific_versions.copy()
                            if prompt_type in general_templates:
                                result[subject][prompt_type].extend(
                                    [f"{v}(fallback)" for v in general_templates[prompt_type]]
                                )
                else:
                    # If subject dir doesn't exist, just add fallbacks
                    for prompt_type, versions in general_templates.items():
                        result[subject][prompt_type] = [f"{v}(fallback)" for v in versions]

        else:
            # List all templates
            for path in self.base_path.rglob('v*.txt'):
                parts = path.relative_to(self.base_path).parts
                if len(parts) != 3:  # subject/type/version.txt
                    continue

                curr_subject = parts[0]
                try:
                    template_type = PromptType(parts[1])
                except ValueError:
                    continue
                version = path.stem.replace('v', '')

                if curr_subject not in result:
                    result[curr_subject] = {}
                if template_type not in result[curr_subject]:
                    result[curr_subject][template_type] = []

                result[curr_subject][template_type].append(version)

        return result