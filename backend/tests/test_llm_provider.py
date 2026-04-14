from unittest.mock import AsyncMock, patch, MagicMock
from app.llm.provider import get_llm_provider


def test_factory_returns_claude_by_default():
    with patch("app.llm.provider.settings") as mock_settings:
        mock_settings.llm_provider = "claude"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-6"
        provider = get_llm_provider()
    from app.llm.claude import ClaudeProvider
    assert isinstance(provider, ClaudeProvider)


def test_factory_returns_ollama():
    with patch("app.llm.provider.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model = "llama3.1"
        provider = get_llm_provider()
    from app.llm.ollama import OllamaProvider
    assert isinstance(provider, OllamaProvider)


async def test_ollama_generate():
    from app.llm.ollama import OllamaProvider
    provider = OllamaProvider("http://localhost:11434", "llama3.1")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "test response"}}
    mock_response.raise_for_status = MagicMock()

    with patch("app.llm.ollama.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await provider.generate("system prompt", "user prompt")

    assert result == "test response"
    mock_client.post.assert_called_once()
    call_json = mock_client.post.call_args[1]["json"]
    assert call_json["model"] == "llama3.1"
    assert call_json["messages"][0]["content"] == "system prompt"


async def test_claude_generate():
    from app.llm.claude import ClaudeProvider

    with patch("app.llm.claude.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="claude response")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = ClaudeProvider("test-key", "claude-sonnet-4-6")
        result = await provider.generate("system", "user")

    assert result == "claude response"
