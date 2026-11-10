"""Recording and replay of model answers.

RecordingProvider wraps a real provider and stores each attempt's answer under a key made from the
provider, model, prompts, schema and feedback. ReplayProvider answers only from those recordings
and fails on anything not recorded, so an eval can be re-scored exactly and offline. Recordings hold
synthetic document text and model answers; they never hold credentials. The directory is git-ignored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import ModelRequest, ProviderError


def request_key(provider: str, model: str, request: ModelRequest, feedback: str | None) -> str:
    payload = json.dumps({"provider": provider, "model": model, "system": request.system, "user": request.user,
                          "schema": request.schema, "temperature": request.temperature, "feedback": feedback},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecordingProvider:
    def __init__(self, inner, directory: Path):
        self._inner, self._dir = inner, directory
        self.name, self.model = inner.name, inner.model
        self._dir.mkdir(parents=True, exist_ok=True)

    def complete_text(self, request: ModelRequest, feedback: str | None = None) -> tuple[str, dict]:
        path = self._dir / f"{request_key(self.name, self.model, request, feedback)}.json"
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            return record["text"], dict(record.get("usage", {}), cached=True)
        text, usage = self._inner.complete_text(request, feedback)
        path.write_text(json.dumps({"provider": self.name, "model": self.model, "schema_name": request.schema_name,
                                    "text": text, "usage": usage}, ensure_ascii=False, indent=1), encoding="utf-8")
        return text, usage


class ReplayProvider:
    def __init__(self, directory: Path, name: str, model: str):
        self._dir, self.name, self.model = directory, name, model

    def complete_text(self, request: ModelRequest, feedback: str | None = None) -> tuple[str, dict]:
        path = self._dir / f"{request_key(self.name, self.model, request, feedback)}.json"
        if not path.exists():
            raise ProviderError(f"replay: no recorded answer for this request in {self._dir} "
                                "(prompt, rules or document changed since the recording?)")
        record = json.loads(path.read_text(encoding="utf-8"))
        return record["text"], dict(record.get("usage", {}), cached=True)
