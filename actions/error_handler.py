import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import functools
from loguru import logger
from memory.long_term import log_action


# ── Retry decorator ────────────────────────────────────────────────────────────

def retry(max_attempts: int = 3, delay: float = 2.0, backoff: float = 2.0):
    """
    Retry a function on failure with exponential backoff.
    max_attempts: total number of tries
    delay: initial wait in seconds
    backoff: multiplier applied to delay after each failure
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"[{fn.__name__}] Failed after {max_attempts} attempts. "
                            f"Last error: {e}"
                        )
                        log_action("error", f"{fn.__name__} failed: {e}")
                        raise
                    logger.warning(
                        f"[{fn.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


# ── Timeout decorator ──────────────────────────────────────────────────────────

def timeout(seconds: int = 30):
    """
    Cancel a function if it runs longer than `seconds`.
    Uses threading so it works on Mac/Linux/Windows.
    """
    import threading

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]

            def target():
                try:
                    result[0] = fn(*args, **kwargs)
                except Exception as e:
                    error[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                logger.error(f"[{fn.__name__}] Timed out after {seconds}s")
                log_action("timeout", f"{fn.__name__} timed out after {seconds}s")
                raise TimeoutError(f"{fn.__name__} exceeded {seconds}s limit")

            if error[0]:
                raise error[0]

            return result[0]
        return wrapper
    return decorator


# ── Fallback decorator ─────────────────────────────────────────────────────────

def fallback(default_message: str = "Action could not be completed."):
    """
    If a skill fails completely, return a safe fallback message
    instead of crashing the agent loop.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"[{fn.__name__}] Unrecoverable error: {e}. Using fallback.")
                log_action("fallback", f"{fn.__name__} used fallback: {e}")
                return f"{default_message}\n\nError details: {e}"
        return wrapper
    return decorator


# ── Input guardrail ────────────────────────────────────────────────────────────

def sanitize_input(text: str, max_length: int = 5000) -> str:
    """
    Basic input sanitization:
    - Strip leading/trailing whitespace
    - Truncate to max_length
    - Remove null bytes
    """
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\x00", "")
    text = text.strip()
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} chars")
        text = text[:max_length] + "... [truncated]"
    return text


# ── Rate limit guard ───────────────────────────────────────────────────────────

class RateLimiter:
    """
    Simple token bucket rate limiter.
    Prevents hammering APIs too fast.
    """
    def __init__(self, calls_per_minute: int = 20):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call_time
        wait_time = self.min_interval - elapsed
        if wait_time > 0:
            logger.debug(f"Rate limiter: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        self.last_call_time = time.time()


# Global rate limiter instance for Groq API calls
groq_limiter = RateLimiter(calls_per_minute=20)


# ── Safe Groq caller ───────────────────────────────────────────────────────────

def safe_call_groq(prompt: str, max_tokens: int = 2000) -> str:
    """
    call_groq() wrapped with retry + timeout + rate limiting.
    Use this instead of call_groq() in any production skill.
    """
    from actions.executor import call_groq

    groq_limiter.wait()

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    @timeout(seconds=30)
    def _call():
        return call_groq(sanitize_input(prompt), max_tokens)

    return _call()


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    # Test retry
    console.rule("[bold blue]Testing retry decorator")
    attempt_count = 0

    @retry(max_attempts=3, delay=1.0)
    def flaky_function():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError(f"Simulated failure on attempt {attempt_count}")
        return "Success on attempt 3"

    result = flaky_function()
    console.print(f"[green]✓ Retry worked: {result}[/green]")

    # Test fallback
    console.rule("[bold blue]Testing fallback decorator")

    @fallback(default_message="Could not complete this action.")
    def always_fails():
        raise RuntimeError("Something went wrong")

    result = always_fails()
    console.print(f"[green]✓ Fallback worked: {result}[/green]")

    # Test sanitize
    console.rule("[bold blue]Testing input sanitization")
    dirty = "  hello\x00world  " + "x" * 6000
    clean = sanitize_input(dirty)
    console.print(f"[green]✓ Sanitized: length {len(dirty)} → {len(clean)}[/green]")

    # Test safe_call_groq
    console.rule("[bold blue]Testing safe Groq call")
    response = safe_call_groq("Say 'error handler works' and nothing else.")
    console.print(f"[green]✓ Groq response: {response}[/green]")