import pytest
from dataclasses import dataclass
from typing import Optional
from ragtrain.hip_agent import ResponseStrategy


# For testing purposes
@dataclass
class AttemptResult:
    answer_index: int
    confidence: float
    explanation: Optional[str] = None


# Import the actual method instead of redefining test class
from ragtrain.hip_agent import select_best_result


def test_empty_results():
    """Test handling of empty results list."""
    assert select_best_result(ResponseStrategy.HIGHEST_CONFIDENCE, []) is None


class TestHighestConfidence:
    """Tests for HIGHEST_CONFIDENCE strategy"""

    def test_single_result(self):
        """Test with single result."""
        result = AttemptResult(answer_index=0, confidence=0.8)
        assert select_best_result(ResponseStrategy.HIGHEST_CONFIDENCE, [result]) == result

    def test_multiple_results(self):
        """Test with multiple results, should pick highest confidence."""
        results = [
            AttemptResult(answer_index=0, confidence=0.8),
            AttemptResult(answer_index=1, confidence=0.9),
            AttemptResult(answer_index=2, confidence=0.7)
        ]
        best = select_best_result(ResponseStrategy.HIGHEST_CONFIDENCE, results)
        assert best.answer_index == 1
        assert best.confidence == 0.9

    def test_equal_confidence(self):
        """Test with equal confidence scores."""
        results = [
            AttemptResult(answer_index=0, confidence=0.8),
            AttemptResult(answer_index=1, confidence=0.8)
        ]
        best = select_best_result(ResponseStrategy.HIGHEST_CONFIDENCE, results)
        assert best.confidence == 0.8
        assert best.answer_index in [0, 1]  # Either is acceptable


class TestMajorityVote:
    """Tests for MAJORITY_VOTE strategy"""

    def test_clear_majority(self):
        """Test with clear majority winner."""
        results = [
            AttemptResult(answer_index=0, confidence=0.7),
            AttemptResult(answer_index=0, confidence=0.8),
            AttemptResult(answer_index=1, confidence=0.9)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE, results)
        assert best.answer_index == 0  # Most votes
        assert best.confidence == 0.8  # Highest confidence among answer 0

    def test_tie_breaking(self):
        """Test tie-breaking behavior."""
        results = [
            AttemptResult(answer_index=0, confidence=0.7),
            AttemptResult(answer_index=1, confidence=0.9),
            AttemptResult(answer_index=0, confidence=0.8),
            AttemptResult(answer_index=1, confidence=0.6)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE, results)
        # Should pick answer with highest confidence among tied answers
        assert best.confidence == 0.9
        assert best.answer_index == 1

    def test_all_different_answers(self):
        """Test when all answers are different."""
        results = [
            AttemptResult(answer_index=0, confidence=0.7),
            AttemptResult(answer_index=1, confidence=0.8),
            AttemptResult(answer_index=2, confidence=0.9)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE, results)
        assert best.confidence == 0.9  # Should pick highest confidence
        assert best.answer_index == 2


class TestMajorityVoteWithConfidence:
    """Tests for MAJORITY_VOTE_WITH_CONFIDENCE strategy"""

    def test_weighted_voting(self):
        """Test weighted voting behavior."""
        results = [
            AttemptResult(answer_index=0, confidence=0.9),  # Total weight 0.9
            AttemptResult(answer_index=1, confidence=0.4),  # Total weight 0.8
            AttemptResult(answer_index=1, confidence=0.4)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE_WITH_CONFIDENCE, results)
        assert best.answer_index == 0  # Highest weighted total
        assert best.confidence == 0.9

    def test_equal_weighted_votes(self):
        """Test behavior with equal weighted votes."""
        results = [
            AttemptResult(answer_index=0, confidence=0.8),
            AttemptResult(answer_index=1, confidence=0.4),
            AttemptResult(answer_index=1, confidence=0.4)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE_WITH_CONFIDENCE, results)
        assert best.confidence == 0.8  # Should pick highest individual confidence
        assert best.answer_index == 0

    def test_single_high_confidence_vs_multiple_low(self):
        """Test one high confidence vs multiple low confidence results."""
        results = [
            AttemptResult(answer_index=0, confidence=0.95),  # Total 0.95
            AttemptResult(answer_index=1, confidence=0.3),  # Total 0.9
            AttemptResult(answer_index=1, confidence=0.3),
            AttemptResult(answer_index=1, confidence=0.3)
        ]
        best = select_best_result(ResponseStrategy.MAJORITY_VOTE_WITH_CONFIDENCE, results)
        assert best.answer_index == 0
        assert best.confidence == 0.95


def test_unknown_strategy():
    """Test handling of unknown strategy."""
    results = [AttemptResult(answer_index=0, confidence=0.8)]
    with pytest.raises(ValueError, match="Unknown response strategy"):
        select_best_result("unknown_strategy", results)