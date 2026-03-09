"""
Base LLM client interface and shared utilities.

Defines the abstract contract that all LLM provider clients must implement,
along with shared retry logic and token usage tracking.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.logger import setup_logger

logger = setup_logger("llm.base")


# ---------------------------------------------------------------------------
# Token usage tracking
# ---------------------------------------------------------------------------


@dataclass
class TokenUsage:
    """Tracks cumulative token usage across LLM calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def record(self, prompt: int, completion: int) -> None:
        """Record tokens from a single API call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_calls += 1

    def summary(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
        }


# ---------------------------------------------------------------------------
# Abstract base client
# ---------------------------------------------------------------------------


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM provider clients.

    Provides built-in retry logic with exponential backoff and
    cumulative token tracking.
    """

    def __init__(
        self,
        model: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.usage = TokenUsage()

    @abstractmethod
    def _call_api(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, int, int]:
        """
        Perform the raw API call to the provider.

        Args:
            messages: Chat-format messages (role/content dicts).
            **kwargs: Provider-specific parameters.

        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens).
        """
        ...

    def generate(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Send a request to the LLM with automatic retry and usage tracking.

        Retries on transient errors with exponential backoff.

        Args:
            messages: Chat-format messages.
            **kwargs: Provider-specific parameters.

        Returns:
            The generated text response.

        Raises:
            LLMClientError: If all retries are exhausted.
        """
        from src.exceptions import LLMClientError

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                text, prompt_tok, completion_tok = self._call_api(messages, **kwargs)
                self.usage.record(prompt_tok, completion_tok)
                logger.info(
                    "LLM call succeeded | model=%s attempt=%d prompt_tok=%d completion_tok=%d",
                    self.model, attempt, prompt_tok, completion_tok,
                )
                return text

            except Exception as exc:
                last_error = exc
                delay = self.base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "LLM call failed | model=%s attempt=%d/%d error=%s retrying_in=%.1fs",
                    self.model, attempt, self.max_retries, exc, delay,
                )
                if attempt < self.max_retries:
                    time.sleep(delay)

        raise LLMClientError(
            f"All {self.max_retries} retries exhausted for model {self.model}: {last_error}"
        )
