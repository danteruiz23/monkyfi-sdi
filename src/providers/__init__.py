"""Model provider layer (SPEC 7.2, D06). Select with MODEL_PROVIDER in .env.

- meta: Muse Spark 1.1 via Meta Model API (OpenAI-compatible). The development model.
- gemini: gemini-3.8-flash via Google's OpenAI-compatible endpoint. The comparison model (D36).

Changing the provider or model requires re-running the evals.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ModelRequest, ModelResponse, Provider, ProviderError, ProviderNotConfigured, generate_json
from .cache import RecordingProvider, ReplayProvider


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from .env into the environment without overriding what is set. No values are printed."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(name.strip(), value)


def provider_from_env(name: str | None = None) -> Provider:
    """The provider named here, or by MODEL_PROVIDER when no name is given."""
    name = (name or os.environ.get("MODEL_PROVIDER") or "").strip().lower()
    if name == "meta":
        from .openai_compatible import meta_from_env
        return meta_from_env()
    if name == "gemini":
        from .openai_compatible import gemini_from_env
        return gemini_from_env()
    raise ProviderNotConfigured(f"MODEL_PROVIDER must be 'meta' or 'gemini' (got {name!r}); set it in .env")


__all__ = ["ModelRequest", "ModelResponse", "Provider", "ProviderError", "ProviderNotConfigured", "RecordingProvider",
           "ReplayProvider", "generate_json", "load_dotenv", "provider_from_env"]
