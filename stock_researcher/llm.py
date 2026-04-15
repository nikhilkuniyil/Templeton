"""Provider-agnostic LLM client layer with an OpenAI Responses adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    """Raised when an LLM request fails cleanly."""


@dataclass(slots=True)
class LLMResponse:
    text: str
    model: str
    provider: str


class LLMClient(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """Generate a text response from the configured provider."""


def _default_post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(slots=True)
class OpenAIResponsesClient:
    """Minimal OpenAI Responses API client."""

    api_key: str
    model: str = "gpt-5.4-mini"
    reasoning_effort: str = "medium"
    base_url: str = "https://api.openai.com/v1/responses"
    post_json: Callable[[str, dict[str, str], dict[str, Any]], dict] = field(
        default=_default_post_json
    )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "reasoning": {"effort": self.reasoning_effort},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.post_json(self.base_url, headers, payload)
        except (HTTPError, URLError, ValueError) as exc:
            raise LLMError(f"OpenAI Responses request failed: {exc}") from exc

        text = self._extract_text(response)
        if not text:
            raise LLMError("OpenAI Responses request returned no text output.")
        return LLMResponse(text=text, model=self.model, provider="openai")

    def _extract_text(self, response: dict) -> str:
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        texts: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
        return "\n\n".join(texts).strip()


@dataclass(slots=True)
class AnthropicMessagesClient:
    """Minimal Anthropic Messages API client."""

    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1200
    anthropic_version: str = "2023-06-01"
    base_url: str = "https://api.anthropic.com/v1/messages"
    post_json: Callable[[str, dict[str, str], dict[str, Any]], dict] = field(
        default=_default_post_json
    )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }
        try:
            response = self.post_json(self.base_url, headers, payload)
        except (HTTPError, URLError, ValueError) as exc:
            raise LLMError(f"Anthropic Messages request failed: {exc}") from exc

        texts: list[str] = []
        for item in response.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        text = "\n\n".join(texts).strip()
        if not text:
            raise LLMError("Anthropic Messages request returned no text output.")
        return LLMResponse(text=text, model=self.model, provider="anthropic")


@dataclass(slots=True)
class GeminiGenerateContentClient:
    """Minimal Gemini generateContent REST client."""

    api_key: str
    model: str = "gemini-2.5-flash"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    post_json: Callable[[str, dict[str, str], dict[str, Any]], dict] = field(
        default=_default_post_json
    )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
        }
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/{self.model}:generateContent"
        try:
            response = self.post_json(url, headers, payload)
        except (HTTPError, URLError, ValueError) as exc:
            raise LLMError(f"Gemini generateContent request failed: {exc}") from exc

        texts: list[str] = []
        for candidate in response.get("candidates", []):
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content", {})
            if not isinstance(content, dict):
                continue
            for part in content.get("parts", []):
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
        text = "\n\n".join(texts).strip()
        if not text:
            raise LLMError("Gemini generateContent request returned no text output.")
        return LLMResponse(text=text, model=self.model, provider="gemini")
