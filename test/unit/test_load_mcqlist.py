import pytest

# Import the function and classes we want to test
# Make sure these imports match your actual module/package structure
from ragtrain.types import MCQ
from ragtrain.mcq import load_mcqlist_from_csv


@pytest.fixture
def sample_csv_content():
    """
    Returns CSV content (as a string) for testing:
    - Two questions
    - Each row has id, question, answer_0..3, correct
    """
    return (
        "id,question,answer_0,answer_1,answer_2,answer_3,correct\n"
        "1,Which planet is known as the Red Planet?,Earth,Venus,Mars,Jupiter,Mars\n"
        "2,What is 2+2?,1,2,3,4,4\n"
    )


def test_load_mcqlist_from_csv(tmp_path, sample_csv_content):
    """
    1. Create a temporary CSV file with sample content.
    2. Call load_qa_from_csv on that file.
    3. Assert the returned QAItem list matches expectations.
    """
    # 1. Write CSV data to a temp file
    test_csv_path = tmp_path / "test_qas.csv"  # tmp_path is an auto pathlib object
    test_csv_path.write_text(sample_csv_content, encoding="utf-8")

    # 2. Call our loader function
    mcq_list = load_mcqlist_from_csv(str(test_csv_path))

    # 3. Run assertions
    # Check we have 2 items
    assert len(mcq_list) == 2

    # Check first item
    first = mcq_list[0]
    assert isinstance(first, MCQ)
    assert first.id == "1"
    assert first.question == "Which planet is known as the Red Planet?"
    assert first.answers == ["Earth", "Venus", "Mars", "Jupiter"]
    # "Mars" was the correct text, so it should be at index 2
    assert first.correct_answer == 2

    # Check second item
    second = mcq_list[1]
    assert second.id == "2"
    assert second.question == "What is 2+2?"
    assert second.answers == ["1", "2", "3", "4"]
    # "4" was the correct text, index 3
    assert second.correct_answer == 3


