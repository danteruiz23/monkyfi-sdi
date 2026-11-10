"""Providers with an OpenAI-compatible chat API. Muse Spark 1.1 via Meta Model API is one (D06).

Configuration comes from environment variables (names in .env.example, values only in .env):
META_MODEL_API_KEY, META_MODEL_API_BASE_URL, META_MODEL_NAME.

Structured output is requested with a JSON Schema response format. If the endpoint rejects that
format, the provider falls back to plain JSON mode once and keeps using it; the answer is still
validated against the schema in base.generate_json, so the fallback never weakens validation.
"""

from __future__ import annotations

import os

from .base import ModelRequest, ProviderError, ProviderNotConfigured


class OpenAICompatibleProvider:
    def __init__(self, name: str, api_key: str, base_url: str, model: str, timeout_s: float = 120.0,
                 max_retries: int = 2):
        from openai import OpenAI  # imported here so tests and replay runs do not need the SDK configured

        self.name, self.model = name, model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=max_retries)
        self._format = "json_schema"

    def _response_format(self, request: ModelRequest) -> dict:
        if self._format == "json_schema":
            return {"type": "json_schema",
                    "json_schema": {"name": request.schema_name, "schema": request.schema, "strict": False}}
        return {"type": "json_object"}

    def complete_text(self, request: ModelRequest, feedback: str | None = None) -> tuple[str, dict]:
        import openai

        messages = [{"role": "system", "content": request.system}, {"role": "user", "content": request.user}]
        if feedback:
            messages.append({"role": "user", "content": feedback})
        try:
            completion = self._client.chat.completions.create(
                model=self.model, messages=messages, temperature=request.temperature,
                response_format=self._response_format(request))
        except openai.BadRequestError as exc:
            if self._format != "json_schema":
                raise ProviderError(f"{self.name}: request rejected: {exc}") from exc
            self._format = "json_object"
            return self.complete_text(request, feedback)
        except openai.OpenAIError as exc:
            raise ProviderError(f"{self.name}: call failed: {type(exc).__name__}: {exc}") from exc
        choice = completion.choices[0]
        usage = completion.usage.model_dump() if getattr(completion, "usage", None) else {}
        usage["response_format"] = self._format
        if choice.finish_reason == "length":
            raise ProviderError(f"{self.name}: answer cut off at the token limit")
        return choice.message.content or "", usage


GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def gemini_from_env() -> OpenAICompatibleProvider:
    """Gemini as comparison model (D36), through Google's OpenAI-compatible endpoint, so both providers
    receive the same messages and schema. Needs GEMINI_API_KEY and GEMINI_MODEL_NAME."""
    missing = [n for n in ("GEMINI_API_KEY", "GEMINI_MODEL_NAME") if not os.environ.get(n)]
    if missing:
        raise ProviderNotConfigured(f"Gemini is not configured: set {', '.join(missing)} in .env "
                                    "(names are listed in .env.example; never commit values)")
    return OpenAICompatibleProvider("gemini", os.environ["GEMINI_API_KEY"], GEMINI_OPENAI_BASE_URL,
                                    os.environ["GEMINI_MODEL_NAME"])


def meta_from_env() -> OpenAICompatibleProvider:
    names = ("META_MODEL_API_KEY", "META_MODEL_API_BASE_URL", "META_MODEL_NAME")
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise ProviderNotConfigured(f"Meta Model API is not configured: set {', '.join(missing)} in .env "
                                    "(names are listed in .env.example; never commit values)")
    return OpenAICompatibleProvider("meta", os.environ["META_MODEL_API_KEY"], os.environ["META_MODEL_API_BASE_URL"],
                                    os.environ["META_MODEL_NAME"])
