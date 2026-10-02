"""Small synchronous clients for external text-generation providers."""

from __future__ import annotations

import json
import logging
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from theravoice.config.settings import LLMSettings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when a configured LLM provider cannot return generated text."""


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate text from a prompt."""


class _JSONHTTPClient:
    provider_name = "LLM"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def _post_json(self, url: str, payload: dict, headers: dict[str, str]) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise LLMError(f"{self.provider_name} request failed with HTTP {error.code}.") from error
        except (TimeoutError, URLError, OSError) as error:
            raise LLMError(f"{self.provider_name} request failed: {error.reason if isinstance(error, URLError) else error}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LLMError(f"{self.provider_name} returned an invalid JSON response.") from error

        if not isinstance(result, dict):
            raise LLMError(f"{self.provider_name} returned an invalid response.")
        return result


class OpenAIClient(_JSONHTTPClient):
    provider_name = "OpenAI"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        super().__init__(api_key, timeout_seconds)
        self._model = model

    def generate(self, prompt: str) -> str:
        result = self._post_json(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            },
            {"Authorization": f"Bearer {self._api_key}"},
        )
        try:
            text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError("OpenAI returned no generated text.") from error
        if not isinstance(text, str) or not text.strip():
            raise LLMError("OpenAI returned no generated text.")
        return text.strip()


class GeminiClient(_JSONHTTPClient):
    provider_name = "Google Gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        super().__init__(api_key, timeout_seconds)
        self._model = model

    def generate(self, prompt: str) -> str:
        model = quote(self._model, safe="-._")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        result = self._post_json(
            url,
            {"contents": [{"parts": [{"text": prompt}]}]},
            {"x-goog-api-key": self._api_key},
        )
        try:
            parts = result["candidates"][0]["content"]["parts"]
            text = "\n".join(part["text"] for part in parts if isinstance(part.get("text"), str))
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise LLMError("Google Gemini returned no generated text.") from error
        if not text.strip():
            raise LLMError("Google Gemini returned no generated text.")
        return text.strip()


def create_llm_client(settings: LLMSettings) -> LLMClient | None:
    """Build the configured client, or return None when LLM use is disabled."""
    provider = settings.provider.strip().lower()
    if provider in {"", "none", "disabled"}:
        return None
    if not settings.api_key:
        logger.warning("LLM provider '%s' is configured without an API key; using deterministic output.", provider)
        return None

    if provider == "openai":
        model = settings.model or "gpt-4o-mini"
        return OpenAIClient(settings.api_key, model, settings.timeout_seconds)
    if provider in {"gemini", "google", "google-gemini"}:
        model = settings.model or "gemini-2.0-flash"
        return GeminiClient(settings.api_key, model, settings.timeout_seconds)

    logger.warning("Unknown LLM provider '%s'; using deterministic output.", provider)
    return None