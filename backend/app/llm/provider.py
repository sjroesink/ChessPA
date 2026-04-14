from typing import Protocol

from app.config import settings


class LLMProvider(Protocol):
    async def generate(self, system: str, user: str) -> str:
        """Send a system + user message to the LLM and return the response text."""
        ...


def get_llm_provider() -> "LLMProvider":
    """Factory: returns configured LLM provider based on settings."""
    if settings.llm_provider == "ollama":
        from app.llm.ollama import OllamaProvider
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    from app.llm.claude import ClaudeProvider
    return ClaudeProvider(settings.anthropic_api_key, settings.anthropic_model)
