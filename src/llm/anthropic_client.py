"""
Anthropic (Claude) LLM client wrapper.

Handles Extended Thinking Mode for Claude 3.7 Sonnet, providing
long-form technical prose generation with deeper reasoning.
"""

from typing import Any

import anthropic

from config.settings import settings
from src.llm.base import BaseLLMClient
from src.logger import setup_logger

logger = setup_logger("llm.anthropic")


class AnthropicClient(BaseLLMClient):
    """
    Client wrapper for the Anthropic API (Claude 3.7 Sonnet).

    Supports Extended Thinking Mode via the `thinking` parameter,
    which allows Claude to reason before producing its final answer.
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        enable_thinking: bool = True,
        thinking_budget: int = 10000,
    ) -> None:
        super().__init__(
            model=model or settings.ANTHROPIC_MODEL,
            max_retries=max_retries,
            base_delay=base_delay,
        )
        self.enable_thinking = enable_thinking
        self.thinking_budget = thinking_budget
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _call_api(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, int, int]:
        """
        Call the Anthropic Messages API.

        When extended thinking is enabled, the request includes a thinking
        block that lets Claude reason deeply before responding.

        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens).
        """
        api_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 16000),
        }

        # System prompt passed as top-level param in Anthropic SDK
        if "system" in kwargs:
            api_kwargs["system"] = kwargs.pop("system")

        # Extended Thinking Mode: adds a 'thinking' budget
        if self.enable_thinking:
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": kwargs.get("thinking_budget", self.thinking_budget),
            }
            # Extended thinking requires at least the thinking budget + max_tokens
            api_kwargs["max_tokens"] = max(
                api_kwargs["max_tokens"],
                self.thinking_budget + 4000,
            )

        # Merge any remaining kwargs
        for k, v in kwargs.items():
            if k not in ("max_tokens", "system", "thinking_budget"):
                api_kwargs[k] = v

        response = self.client.messages.create(**api_kwargs)

        # Extract the text content (skip thinking blocks)
        text_parts: list[str] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        response_text = "\n".join(text_parts)
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens

        return response_text, prompt_tokens, completion_tokens
