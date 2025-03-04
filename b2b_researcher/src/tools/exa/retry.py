import time
import functools
import logging
from typing import TypeVar, Callable, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_on_error(max_retries: int = 10, delay: float = 1.0) -> Callable:
    """
    A decorator that retries a function if it raises an exception.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        delay (float): Delay in seconds between retries
        
    Returns:
        Callable: Decorated function that will retry on failure
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} attempts. Last error: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {retries}/{max_retries} failed: {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            
            # This should never be reached due to the raise in the except block
            raise RuntimeError("Unexpected end of retry loop")
            
        return wrapper
    return decorator
