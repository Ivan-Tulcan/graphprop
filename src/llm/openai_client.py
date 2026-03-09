"""
OpenAI LLM client wrapper.

Handles GPT-5.2 Pro calls for logical structuring and schema
generation tasks within the document factory pipeline.
"""

from typing import Any

import openai

from config.settings import settings
from src.llm.base import BaseLLMClient
from src.logger import setup_logger

logger = setup_logger("llm.openai")


class OpenAIClient(BaseLLMClient):
    """
    Client wrapper for the OpenAI API (GPT-5.2 Pro).

    Used primarily for generating structured JSON skeletons where
    logical consistency and schema adherence are critical.
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        super().__init__(
            model=model or settings.OPENAI_MODEL,
            max_retries=max_retries,
            base_delay=base_delay,
        )
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def _call_api(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, int, int]:
        """
        Call the OpenAI Chat Completions API.

        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens).
        """
        api_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 8000),
            "temperature": kwargs.get("temperature", 0.3),
        }

        # JSON mode: instruct the model to output valid JSON
        if kwargs.get("json_mode", False):
            api_kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**api_kwargs)

        choice = response.choices[0]
        response_text = choice.message.content or ""

        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        return response_text, prompt_tokens, completion_tokens
