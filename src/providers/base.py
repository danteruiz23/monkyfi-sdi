"""Provider interface (SPEC 7.2, D06). Every model call in the project goes through here.

A provider turns (system prompt, user message, JSON Schema) into a JSON object. The object is
validated against the schema before it is returned; an invalid answer is retried a bounded number
of times with the validation error, then raised. Nothing a model returns is used unvalidated.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Protocol

from jsonschema import Draft202012Validator


class ProviderError(RuntimeError):
    """The provider could not produce a valid answer (configuration, network or invalid output)."""


class ProviderNotConfigured(ProviderError):
    """Required environment variables are missing. Values live only in .env (CLAUDE.md rule 2)."""


@dataclass
class ModelRequest:
    system: str
    user: str
    schema: dict
    schema_name: str
    temperature: float = 0.0


@dataclass
class ModelResponse:
    data: dict
    provider: str
    model: str
    raw_text: str
    attempts: int = 1
    latency_s: float = 0.0
    usage: dict = field(default_factory=dict)
    cached: bool = False


class Provider(Protocol):
    name: str
    model: str

    def complete_text(self, request: ModelRequest, feedback: str | None = None) -> tuple[str, dict]:
        """Return (raw text, usage) for one attempt. `feedback` explains why the last attempt was rejected."""


def parse_json_object(text: str) -> dict:
    """The JSON object in a model answer. Tolerates a fenced code block; nothing else."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("answer is not a JSON object")
    return value


def generate_json(provider: Provider, request: ModelRequest, max_attempts: int = 3) -> ModelResponse:
    """One structured call with schema validation and bounded retries."""
    validator = Draft202012Validator(request.schema)
    feedback, started, last_text = None, time.monotonic(), ""
    usage: dict = {}
    for attempt in range(1, max_attempts + 1):
        last_text, usage = provider.complete_text(request, feedback)
        try:
            data = parse_json_object(last_text)
        except ValueError as exc:  # json.JSONDecodeError is a ValueError
            feedback = f"Your previous answer was not a valid JSON object ({exc}). Answer with JSON only."
            continue
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if not errors:
            return ModelResponse(data=data, provider=provider.name, model=provider.model, raw_text=last_text,
                                 attempts=attempt, latency_s=round(time.monotonic() - started, 3), usage=usage)
        feedback = ("Your previous answer did not match the required schema: "
                    + "; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:5])
                    + ". Answer again with JSON that matches the schema.")
    raise ProviderError(f"{provider.name}/{provider.model}: no valid answer after {max_attempts} attempts; "
                        f"last answer starts with {last_text[:200]!r}")
