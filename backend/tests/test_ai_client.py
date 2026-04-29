"""Tests for AI client — Claude API wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.client import AIClient, AIServiceError
from app.config import settings


@pytest.fixture
def ai_client():
    """Fresh AIClient instance (lazy init, no actual API key needed)."""
    return AIClient()


class TestAIClientDisabled:
    def test_raises_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", False)
        client = AIClient()
        with pytest.raises(AIServiceError, match="disabled"):
            _ = client.client

    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "")
        client = AIClient()
        with pytest.raises(AIServiceError, match="ANTHROPIC_API_KEY"):
            _ = client.client


class TestAIClientComplete:
    def test_returns_text_from_response(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello from Claude"

        mock_response = MagicMock()
        mock_response.content = [mock_block]

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            result = client.complete("system", "user message")
            assert result == "Hello from Claude"

    def test_returns_empty_string_for_no_content(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        mock_response = MagicMock()
        mock_response.content = []

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            result = client.complete("system", "user message")
            assert result == ""

    def test_retries_on_status_error(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        import anthropic

        mock_anthropic = MagicMock()
        # First call fails, second succeeds
        mock_anthropic.messages.create.side_effect = [
            anthropic.APIStatusError("server error", response=MagicMock(), body={}),
            _make_text_response("retry success"),
        ]

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            result = client.complete("system", "user message")
            assert result == "retry success"

    def test_retries_on_timeout_error(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        import anthropic

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.side_effect = [
            anthropic.APITimeoutError("timeout"),
            _make_text_response("timeout recovery"),
        ]

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            result = client.complete("system", "user message")
            assert result == "timeout recovery"

    def test_raises_after_two_failures(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        import anthropic

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.side_effect = anthropic.APIStatusError(
            "persistent error", response=MagicMock(), body={}
        )

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            with pytest.raises(AIServiceError, match="failed after retries"):
                client.complete("system", "user message")

    def test_respects_custom_model_and_max_tokens(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_text_response("ok")

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            client.complete("sys", "msg", max_tokens=100, temperature=0.5, model="claude-opus-4-7")
            call_kwargs = mock_anthropic.messages.create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 100
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["model"] == "claude-opus-4-7"


class TestAIClientStream:
    def test_yields_text_chunks(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        mock_stream = MagicMock()
        mock_stream.text_stream = ["Hello", " world", "!"]
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        mock_anthropic = MagicMock()
        mock_anthropic.messages.stream.return_value = mock_stream

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            chunks = list(client.complete_stream("sys", "msg"))
            assert chunks == ["Hello", " world", "!"]

    def test_raises_on_status_error(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

        import anthropic

        mock_anthropic = MagicMock()
        mock_anthropic.messages.stream.side_effect = anthropic.APIStatusError(
            "stream error", response=MagicMock(), body={}
        )

        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            client = AIClient()
            with pytest.raises(AIServiceError, match="streaming failed"):
                list(client.complete_stream("sys", "msg"))


def _make_text_response(text: str):
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = text
    mock_resp = MagicMock()
    mock_resp.content = [mock_block]
    return mock_resp
