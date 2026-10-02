"""Provider request formatting and configuration tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from theravoice.config.settings import LLMSettings
from theravoice.llm.client import GeminiClient, LLMError, OpenAIClient, create_llm_client


def _mock_response(body: dict) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(body).encode("utf-8")
    return response


def test_openai_client_sends_chat_completion_request():
    with patch("theravoice.llm.client.urlopen", return_value=_mock_response(
        {"choices": [{"message": {"content": "Generated summary"}}]}
    )) as open_url:
        client = OpenAIClient("secret", "test-model", 3.0)
        assert client.generate("prompt") == "Generated summary"

    request = open_url.call_args.args[0]
    assert request.full_url.endswith("/v1/chat/completions")
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data)["model"] == "test-model"


def test_gemini_client_sends_generate_content_request():
    with patch("theravoice.llm.client.urlopen", return_value=_mock_response(
        {"candidates": [{"content": {"parts": [{"text": "Generated summary"}]}}]}
    )) as open_url:
        client = GeminiClient("secret", "test-model", 3.0)
        assert client.generate("prompt") == "Generated summary"

    request = open_url.call_args.args[0]
    assert "/models/test-model:generateContent" in request.full_url
    assert "key=" not in request.full_url
    assert request.get_header("X-goog-api-key") == "secret"
    assert json.loads(request.data)["contents"][0]["parts"][0]["text"] == "prompt"


def test_llm_factory_is_disabled_without_provider_or_api_key():
    assert create_llm_client(LLMSettings()) is None
    assert create_llm_client(LLMSettings(provider="openai")) is None


def test_llm_factory_selects_configured_provider():
    assert isinstance(
        create_llm_client(LLMSettings(provider="openai", api_key="secret")), OpenAIClient
    )
    assert isinstance(
        create_llm_client(LLMSettings(provider="gemini", api_key="secret")), GeminiClient
    )


def test_openai_client_converts_timeout_to_llm_error():
    with patch("theravoice.llm.client.urlopen", side_effect=TimeoutError("timed out")) as open_url:
        client = OpenAIClient("secret", "test-model", 3.0)
        with pytest.raises(LLMError, match="request failed"):
            client.generate("prompt")

    assert open_url.call_args.kwargs["timeout"] == 3.0