"""Scripted provider for tests. It never calls a network and is never selected by MODEL_PROVIDER.

`respond(request, feedback)` returns the answer text (or a dict, serialized as JSON). Its results
measure the pipeline around the model, never model accuracy, and must not be reported as such.
"""

from __future__ import annotations

import json
from typing import Callable

from .base import ModelRequest


class ScriptedProvider:
    def __init__(self, respond: Callable[[ModelRequest, str | None], str | dict], name: str = "scripted",
                 model: str = "scripted-test"):
        self._respond, self.name, self.model = respond, name, model
        self.calls: list[tuple[ModelRequest, str | None]] = []

    def complete_text(self, request: ModelRequest, feedback: str | None = None) -> tuple[str, dict]:
        self.calls.append((request, feedback))
        answer = self._respond(request, feedback)
        return (answer if isinstance(answer, str) else json.dumps(answer)), {}
