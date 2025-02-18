import pytest
from unittest.mock import Mock, patch
import time
from openai import OpenAIError, APIError, RateLimitError

from ragtrain.util import retry_with_exponential_backoff


# Mock response for rate limit errors
class MockResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


# Mock OpenAI errors for testing
class MockRateLimitError(RateLimitError):
    def __init__(self, headers=None):
        self.response = MockResponse(headers=headers)
        self.message = "Rate limit exceeded"


class MockAPIError(APIError):
    def __init__(self):
        self.message = "API error"
        self.response = None


@pytest.fixture
def mock_time_sleep():
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep


def test_successful_call(mock_time_sleep):
    """Test successful API call with no retries needed."""
    expected_result = {"response": "success"}

    @retry_with_exponential_backoff()
    def mock_api_call():
        return expected_result

    result = mock_api_call()
    assert result == expected_result
    mock_time_sleep.assert_not_called()


def test_rate_limit_with_retry_after(mock_time_sleep):
    """Test rate limit error with retry-after header."""
    expected_result = {"response": "success"}
    retry_after = 15

    mock_func = Mock(side_effect=[
        MockRateLimitError(headers={'retry-after': str(retry_after)}),
        expected_result
    ])

    @retry_with_exponential_backoff(max_retries=3)
    def mock_api_call():
        return mock_func()

    result = mock_api_call()
    assert result == expected_result
    mock_time_sleep.assert_called_once_with(retry_after)
    assert mock_func.call_count == 2


def test_rate_limit_without_retry_after(mock_time_sleep):
    """Test rate limit error without retry-after header."""
    expected_result = {"response": "success"}

    mock_func = Mock(side_effect=[
        MockRateLimitError(),  # No headers
        expected_result
    ])

    @retry_with_exponential_backoff(max_retries=3)
    def mock_api_call():
        return mock_func()

    result = mock_api_call()
    assert result == expected_result
    mock_time_sleep.assert_called_once_with(20)  # Default wait time
    assert mock_func.call_count == 2


def test_exponential_backoff(mock_time_sleep):
    """Test exponential backoff for non-rate-limit errors."""
    expected_result = {"response": "success"}

    mock_func = Mock(side_effect=[
        MockAPIError(),
        MockAPIError(),
        expected_result
    ])

    @retry_with_exponential_backoff(
        max_retries=3,
        initial_delay=1,
        exponential_base=2
    )
    def mock_api_call():
        return mock_func()

    result = mock_api_call()
    assert result == expected_result

    # Check exponential backoff timing (excluding jitter)
    assert mock_time_sleep.call_count == 2
    calls = mock_time_sleep.call_args_list
    assert 1.0 <= float(calls[0][0][0]) <= 1.1  # Initial delay + max jitter
    assert 2.0 <= float(calls[1][0][0]) <= 2.1  # Second delay + max jitter


def test_max_retries_exceeded(mock_time_sleep):
    """Test error raised when max retries exceeded."""
    mock_func = Mock(side_effect=MockAPIError())

    @retry_with_exponential_backoff(max_retries=2)
    def mock_api_call():
        return mock_func()

    with pytest.raises(MockAPIError):
        mock_api_call()

    assert mock_func.call_count == 3  # Initial + 2 retries
    assert mock_time_sleep.call_count == 2


def test_non_retryable_error():
    """Test that non-retryable errors are raised immediately."""
    mock_func = Mock(side_effect=ValueError("Non-retryable error"))

    @retry_with_exponential_backoff()
    def mock_api_call():
        return mock_func()

    with pytest.raises(ValueError):
        mock_api_call()

    assert mock_func.call_count == 1  # Only called once


def test_custom_error_types(mock_time_sleep):
    """Test retry with custom error types."""
    expected_result = {"response": "success"}

    mock_func = Mock(side_effect=[
        ValueError("Custom error"),
        expected_result
    ])

    @retry_with_exponential_backoff(error_types=(ValueError,))
    def mock_api_call():
        return mock_func()

    result = mock_api_call()
    assert result == expected_result
    assert mock_func.call_count == 2


def test_mixed_errors(mock_time_sleep):
    """Test handling of mixed error types."""
    expected_result = {"response": "success"}

    mock_func = Mock(side_effect=[
        MockRateLimitError(headers={'retry-after': '10'}),
        MockAPIError(),
        MockAPIError(),
        expected_result
    ])

    @retry_with_exponential_backoff(max_retries=3)
    def mock_api_call():
        return mock_func()

    result = mock_api_call()
    assert result == expected_result
    assert mock_func.call_count == 4

    # Verify different wait times for different error types
    calls = mock_time_sleep.call_args_list
    assert len(calls) == 3
    assert float(calls[0][0][0]) == 10  # Rate limit retry-after
    assert 1.0 <= float(calls[1][0][0]) <= 1.1  # First exponential backoff + jitter
    assert 2.0 <= float(calls[2][0][0]) <= 2.1  # Second exponential backoff + jitter