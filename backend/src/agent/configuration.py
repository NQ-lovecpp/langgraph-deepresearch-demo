import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional, Literal
import yaml

from langchain_core.runnables import RunnableConfig


def load_config() -> dict:
    """Load configuration from config.yaml file."""
    # Look for config.yaml in the project root (parent of backend directory)
    config_paths = [
        Path(__file__).parent.parent.parent.parent.parent / "config.yaml",  # From src/agent/
        Path(__file__).parent.parent.parent.parent / "config.yaml",  # Alternative path
        Path.cwd() / "config.yaml",  # Current working directory
        Path.cwd().parent / "config.yaml",  # Parent of current working directory
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
    
    # Return default configuration if no config file found
    return {
        "active_provider": "google",
        "google": {
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "query_generator_model": "models/gemini-2.5-flash",
            "reflection_model": "models/gemini-2.5-flash",
            "answer_model": "models/gemini-2.5-pro",
        },
        "openrouter": {
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "query_generator_model": "anthropic/claude-3.5-sonnet",
            "reflection_model": "anthropic/claude-3.5-sonnet",
            "answer_model": "anthropic/claude-3.5-sonnet",
            "exa_api_key": "",
        },
        "local": {
            "base_url": "http://localhost:8080/v1",
            "model_name": "gpt-3.5-turbo",
            "query_generator_model": "gpt-3.5-turbo",
            "reflection_model": "gpt-3.5-turbo",
            "answer_model": "gpt-3.5-turbo",
            "exa_api_key": "",
        },
    }


# Load config at module level
_config = load_config()


def get_active_provider() -> str:
    """Get the active provider from configuration."""
    return _config.get("active_provider", "google")


def get_provider_config(provider: Optional[str] = None) -> dict:
    """Get configuration for the specified provider."""
    if provider is None:
        provider = get_active_provider()
    return _config.get(provider, {})


class Configuration(BaseModel):
    """The configuration for the agent."""

    # Provider selection
    provider: Literal["google", "openrouter", "local"] = Field(
        default_factory=get_active_provider,
        metadata={"description": "The provider to use: google, openrouter, or local"},
    )

    query_generator_model: str = Field(
        default="",
        metadata={
            "description": "The name of the language model to use for the agent's query generation."
        },
    )

    reflection_model: str = Field(
        default="",
        metadata={
            "description": "The name of the language model to use for the agent's reflection."
        },
    )

    answer_model: str = Field(
        default="",
        metadata={
            "description": "The name of the language model to use for the agent's answer."
        },
    )

    number_of_initial_queries: int = Field(
        default=3,
        metadata={"description": "The number of initial search queries to generate."},
    )

    max_research_loops: int = Field(
        default=2,
        metadata={"description": "The maximum number of research loops to perform."},
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Set default models based on provider if not specified
        provider_config = get_provider_config(self.provider)
        if not self.query_generator_model:
            self.query_generator_model = provider_config.get("query_generator_model", "")
        if not self.reflection_model:
            self.reflection_model = provider_config.get("reflection_model", "")
        if not self.answer_model:
            self.answer_model = provider_config.get("answer_model", "")

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)

    def get_api_key(self) -> str:
        """Get the API key for the current provider."""
        provider_config = get_provider_config(self.provider)
        if self.provider == "google":
            return provider_config.get("api_key", "") or os.getenv("GEMINI_API_KEY", "")
        elif self.provider == "openrouter":
            return provider_config.get("api_key", "")
        else:
            return ""  # Local doesn't need API key

    def get_base_url(self) -> Optional[str]:
        """Get the base URL for the current provider."""
        provider_config = get_provider_config(self.provider)
        if self.provider == "openrouter":
            return provider_config.get("base_url", "https://openrouter.ai/api/v1")
        elif self.provider == "local":
            return provider_config.get("base_url", "http://localhost:8080/v1")
        return None

    def get_exa_api_key(self) -> str:
        """Get the Exa API key for OpenRouter or local providers."""
        provider_config = get_provider_config(self.provider)
        return provider_config.get("exa_api_key", "")
