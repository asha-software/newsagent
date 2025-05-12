import os
from typing import Any, Dict, Optional, Literal, Union
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

# Map model names to their providers
MODEL_PROVIDERS = {
    # OpenAI models (NOTE: many models don't support formatted output the we're using it for Ollama. We'll likely have to move to pydantic to support both with the same schema models)
    "gpt-4o-mini": "openai",

    # Anthropic models
    "claude-3-opus-20240229": "anthropic",
    "claude-3-sonnet-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "claude-2.0": "anthropic",
    "claude-2.1": "anthropic",

    # Ollama models
    "llama3": "ollama",
    "llama3:8b": "ollama",
    "llama3:70b": "ollama",
    "mistral-nemo": "ollama",
    "mistral:7b": "ollama",
    "mixtral": "ollama",
    "phi3": "ollama",
    "qwq": "ollama",
    "deepseek-r1:32b": "ollama",
}

# Allow explicit provider override


def get_chat_model(
    model_name: str,
    format_output: Optional[Dict] = None,
    **kwargs
) -> BaseChatModel:
    """
    Factory function to create the appropriate chat model based on model name or explicit provider.

    Args:
        model_name: Name of the model to use
        temperature: Temperature setting for the model
        format: Output format schema
        provider: Explicitly specify the provider (overrides model name lookup)
        **kwargs: Additional arguments to pass to the model constructor

    Returns:
        A chat model instance of the appropriate type
    """
    # Determine provider - use explicit provider if specified, otherwise look up in the mapping
    model_provider = MODEL_PROVIDERS.get(model_name)

    # If we can't determine provider from mapping or explicit override, use Ollama as fallback
    if not model_provider:
        print(f"Warning: Unknown model '{model_name}'."
              f"Add this model to MODEL_PROVIDERS explicitly to enable support.")

    # Create the appropriate model type
    if model_provider == "openai":
        return ChatOpenAI(
            model=model_name,
            temperature=0,
            model_kwargs={
                "response_format":
                {
                    "type": "json_schema",
                    "json_schema": format_output
                }
            }
        )

    # elif model_provider == "anthropic":
    #     return ChatAnthropic(
    #         model=model_name,
    #         temperature=0,
    #         **({"response_format": format} if format else {}),
    #         **kwargs
    #     )
    elif model_provider == "ollama":  # ollama
        ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434")
        model_kwargs = {
            "model": model_name,
            "temperature": 0,
            "base_url": ollama_base_url,
            "num_ctx": 128000,
            **kwargs
        }
        if format_output:
            model_kwargs["format"] = format_output
        return ChatOllama(**model_kwargs)

    raise ValueError(
        f"Unknown model '{model_name}', can't build an LLM on that model.")
