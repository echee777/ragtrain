import time
import random
import functools
import logging
from typing import Type, Union, Callable
from openai import OpenAI, OpenAIError, APIError, RateLimitError

logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(
        max_retries: int = 5,
        initial_delay: float = 1,
        exponential_base: float = 2,
        error_types: Union[Type[Exception], tuple[Type[Exception], ...]] = (
                RateLimitError,
                APIError
        )
) -> Callable:
    """
    Decorator that implements exponential backoff for OpenAI API calls.

    For RateLimitError, uses the retry-after header from OpenAI.
    For other errors, uses exponential backoff with jitter.

    Args:
        max_retries: Maximum number of retries before giving up
        initial_delay: Initial delay between retries in seconds
        exponential_base: Base for exponential backoff
        error_types: Tuple of error types to catch and retry

    Returns:
        Callable: Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):  # +1 to include initial attempt
                try:
                    return func(*args, **kwargs)

                except RateLimitError as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Failed after {max_retries} retries. "
                            f"Last error: {str(last_exception)}"
                        )
                        raise last_exception

                    # Default to 20 seconds if no header
                    wait_time = 20

                    # Try to get retry-after from response headers
                    if hasattr(e, 'response'):
                        headers = getattr(e.response, 'headers', {})
                        if 'retry-after' in headers:
                            wait_time = float(headers['retry-after'])

                    logger.warning(
                        f"Rate limit hit on attempt {attempt + 1}/{max_retries}. "
                        f"Waiting {wait_time} seconds as specified by API..."
                    )
                    time.sleep(wait_time)

                except error_types as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Failed after {max_retries} retries. "
                            f"Last error: {str(last_exception)}"
                        )
                        raise last_exception

                    # Add jitter: random value between 0 and 0.1 seconds
                    jitter = random.uniform(0, 0.1)
                    wait_time = delay + jitter

                    logger.warning(
                        f"OpenAI API call failed on attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time:.2f} seconds... "
                        f"Error: {str(e)}"
                    )

                    time.sleep(wait_time)
                    delay *= exponential_base  # Increase delay for next iteration

                except Exception as e:
                    # Don't retry on non-matching exceptions
                    logger.error(f"Non-retryable error occurred: {str(e)}")
                    raise e

        return wrapper

    return decorator


# Example usage:
@retry_with_exponential_backoff()
def make_openai_call(client: OpenAI, prompt: str) -> dict:
    """Example function showing usage of the decorator."""
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )