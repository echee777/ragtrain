import pytest
from pathlib import Path
import tempfile
import shutil
from ragtrain.prompt_templates import TemplateManager, PromptType
from ragtrain.types import SubjectDomain

@pytest.fixture
def template_manager():
    """Fixture to create a temporary template directory and manager instance."""
    test_dir = tempfile.mkdtemp()

    def create_template(relative_path: str, content: str):
        full_path = Path(test_dir) / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)

    # Create required general templates first
    for prompt_type in PromptType:
        create_template(
            f'general/{prompt_type.value}/v1.txt',
            f"GENERAL template for {prompt_type.value}"
        )
        create_template(
            f'general/{prompt_type.value}/v2.txt',
            f"GENERAL template v2 for {prompt_type.value}"
        )

    # Create biology templates (subset)
    create_template(
        f'biology/{PromptType.COT.value}/v1.txt',
        "Given a biology question about {topic}, let's approach this step by step:\n1) First..."
    )
    create_template(
        f'biology/{PromptType.FEW_SHOT.value}/v1.txt',
        "Here are some example biology questions:\n1) What is..."
    )
    create_template(
        f'biology/{PromptType.COT.value}/v2.txt',
        "For this biology question about {topic}, let's analyze systematically:\n1) Consider..."
    )

    manager = TemplateManager(test_dir)
    yield manager
    shutil.rmtree(test_dir)


def test_get_template_success(template_manager):
    """Test successful template retrieval."""
    template = template_manager.get_template('biology', PromptType.COT, '1')
    assert "Given a biology question" in template


def test_get_template_v2(template_manager):
    """Test getting v2 template."""
    template = template_manager.get_template('biology', PromptType.COT, '2')
    assert "For this biology question" in template


def test_get_general_template(template_manager):
    """Test getting general template directly."""
    template = template_manager.get_template(SubjectDomain.GENERAL, PromptType.COT, '1')
    assert "GENERAL template for cot" in template


def test_fallback_to_general(template_manager):
    """Test fallback to general template when biology template missing."""
    # Try to get a template type that doesn't exist in biology
    template = template_manager.get_template('biology', PromptType.CONTRARIAN, '1')
    assert "GENERAL template for contrarian" in template


def test_get_template_not_found(template_manager):
    """Test retrieving non-existent template."""
    with pytest.raises(FileNotFoundError) as exc_info:
        template_manager.get_template('physics', PromptType.COT, '1')
    assert "Subject directory not found" in str(exc_info.value)


def test_list_all_templates(template_manager):
    """Test listing all available templates."""
    templates = template_manager.list_templates()

    assert 'biology' in templates
    assert 'general' in templates
    assert PromptType.COT in templates['biology']
    assert PromptType.FEW_SHOT in templates['biology']
    assert '1' in templates['biology'][PromptType.COT]
    assert '2' in templates['biology'][PromptType.COT]
    assert '1' in templates['biology'][PromptType.FEW_SHOT]


def test_list_subject_templates(template_manager):
    """Test listing templates for a specific subject."""
    biology_templates = template_manager.list_templates('biology')['biology']

    assert PromptType.COT in biology_templates
    assert PromptType.FEW_SHOT in biology_templates

    # Check specific templates exist
    cot_versions = biology_templates[PromptType.COT]
    assert '1' in cot_versions
    assert '2' in cot_versions
    assert '1(fallback)' in cot_versions
    assert '2(fallback)' in cot_versions

    # Check fallback versions exist for types without specific templates
    for prompt_type in PromptType:
        if prompt_type not in [PromptType.COT, PromptType.FEW_SHOT]:
            assert prompt_type in biology_templates
            assert all('(fallback)' in v for v in biology_templates[prompt_type])


def test_list_nonexistent_subject(template_manager):
    """Test listing templates for a non-existent subject."""
    physics_templates = template_manager.list_templates('physics')
    assert physics_templates == {'physics': {}}


def test_template_structure(template_manager):
    """Test the structure and format of templates."""
    cot_template = template_manager.get_template('biology', PromptType.COT, '1')
    few_shot_template = template_manager.get_template('biology', PromptType.FEW_SHOT, '1')

    assert '{topic}' in cot_template
    assert 'step by step' in cot_template.lower()
    assert 'example' in few_shot_template.lower()


def test_case_insensitive_subject(template_manager):
    """Test that subject handling is case insensitive."""
    template1 = template_manager.get_template('BIOLOGY', PromptType.COT, '1')
    template2 = template_manager.get_template('biology', PromptType.COT, '1')
    assert template1 == template2


def test_initialization_requires_general_templates(template_manager):
    """Test that initialization fails if general templates are missing."""
    test_dir = tempfile.mkdtemp()

    # Create directory without general templates
    Path(test_dir).mkdir(exist_ok=True)

    with pytest.raises(FileNotFoundError) as exc_info:
        TemplateManager(test_dir)
    assert "Required general template missing" in str(exc_info.value)

    shutil.rmtree(test_dir)


def test_invalid_template_type(template_manager):
    """Test that invalid template types are handled properly."""
    # Create an invalid template type directory
    invalid_path = Path(template_manager.base_path) / 'biology/invalid_type/v1.txt'
    invalid_path.parent.mkdir(parents=True, exist_ok=True)
    invalid_path.write_text("Invalid template")

    # This invalid type should be skipped in listings
    templates = template_manager.list_templates()
    assert 'invalid_type' not in {t.value for t in templates['biology'].keys()}


def test_no_fallback_for_unknown_subject(template_manager):
    """Test that unknown subjects don't get fallback templates."""
    with pytest.raises(FileNotFoundError) as exc_info:
        template_manager.get_template('chemistry', PromptType.COT, '1')
    assert "Subject directory not found" in str(exc_info.value)


def test_partial_subject_directory(template_manager):
    """Test handling of partial subject directory structure."""
    # Create biology directory with only COT templates
    bio_dir = Path(template_manager.base_path) / "biology"
    if bio_dir.exists():
        shutil.rmtree(bio_dir)

    bio_dir.mkdir(exist_ok=True)
    cot_dir = bio_dir / PromptType.COT.value
    cot_dir.mkdir(exist_ok=True)
    with open(cot_dir / "v1.txt", 'w') as f:
        f.write("Biology COT template")

    # COT should use biology template
    cot_template = template_manager.get_template('biology', PromptType.COT, '1')
    assert "Biology COT template" in cot_template

    # RAG should fallback to general
    contrarian_template = template_manager.get_template('biology', PromptType.CONTRARIAN, '1')
    assert "GENERAL template for contrarian" in contrarian_template

    # Check template listing
    templates = template_manager.list_templates('biology')['biology']
    assert PromptType.COT in templates  # Has specific template
    assert '1' in templates[PromptType.COT]  # Has specific version

    # Should have fallbacks for other types
    for prompt_type in PromptType:
        if prompt_type != PromptType.COT:
            assert prompt_type in templates
            assert all('(fallback)' in v for v in templates[prompt_type])
