"""
LLM Client Factory.

Provides a single entry point for obtaining configured LLM clients
without coupling the rest of the application to specific provider SDKs.
"""

from typing import Literal

from src.llm.anthropic_client import AnthropicClient
from src.llm.base import BaseLLMClient
from src.llm.openai_client import OpenAIClient


def get_llm_client(
    provider: Literal["anthropic", "openai"],
    **kwargs,
) -> BaseLLMClient:
    """
    Factory function that returns the appropriate LLM client.

    Args:
        provider: Which LLM provider to use ('anthropic' or 'openai').
        **kwargs: Provider-specific configuration overrides.

    Returns:
        Configured BaseLLMClient subclass instance.

    Raises:
        ValueError: If an unknown provider is specified.
    """
    if provider == "anthropic":
        return AnthropicClient(**kwargs)
    elif provider == "openai":
        return OpenAIClient(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
