from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class OllamaError(RuntimeError):
    """Raised when the local Ollama server cannot complete a request."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class OllamaClient:
    """Small dependency-free client for Ollama's streaming chat endpoint."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def stream_chat(self, messages: Sequence[ChatMessage]) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": [message.as_dict() for message in messages],
            "stream": True,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = request.urlopen(http_request, timeout=self.timeout)
        except (OSError, error.URLError, error.HTTPError) as exc:
            raise OllamaError(f"Unable to reach Ollama at {self.base_url}: {exc}") from exc

        with response:
            for raw_line in response:
                if not raw_line.strip():
                    continue
                try:
                    chunk: dict[str, Any] = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise OllamaError("Ollama returned invalid JSON.") from exc
                if chunk.get("error"):
                    raise OllamaError(str(chunk["error"]))
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield str(content)

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        return "".join(self.stream_chat(messages))

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.load(response)
        except (OSError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Unable to embed with Ollama: {exc}") from exc
        embeddings = body.get("embeddings")
        if not embeddings or not isinstance(embeddings[0], list):
            raise OllamaError("Ollama returned no embedding.")
        return [float(value) for value in embeddings[0]]
