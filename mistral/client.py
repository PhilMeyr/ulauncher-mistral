"""Minimal HTTP client for the Mistral API (stdlib only, zero dependencies)."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any, Protocol

from mistral.errors import ApiError, ApiKeyMissingError, ApiTimeoutError, NetworkError

if TYPE_CHECKING:
    from collections.abc import Iterator

API_BASE = "https://api.mistral.ai/v1"

Message = dict[str, str]  # {"role": ..., "content": ...}


class ChatProvider(Protocol):
    """Interface the commands depend on (DIP) — allows swapping the backend."""

    def chat(self, messages: list[Message], model: str, max_tokens: int) -> str: ...

    def chat_stream(
        self, messages: list[Message], model: str, max_tokens: int
    ) -> Iterator[str]: ...

    def list_models(self) -> list[str]: ...


class MistralClient:
    """`ChatProvider` implementation on top of the Mistral REST API via urllib."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        if not api_key:
            raise ApiKeyMissingError
        self._api_key = api_key
        self._timeout = timeout

    # -- Public API ---------------------------------------------------------

    def chat(self, messages: list[Message], model: str, max_tokens: int) -> str:
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        data = self._request_json("POST", "/chat/completions", payload)
        return data["choices"][0]["message"]["content"]

    def chat_stream(self, messages: list[Message], model: str, max_tokens: int) -> Iterator[str]:
        """Iterate over the text deltas returned as SSE (`stream: true`)."""
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True}
        with self._open("POST", "/chat/completions", payload) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:") :].strip()
                if chunk == "[DONE]":
                    break
                delta = json.loads(chunk)["choices"][0]["delta"].get("content")
                if delta:
                    yield delta

    def list_models(self) -> list[str]:
        data = self._request_json("GET", "/models")
        return sorted({entry["id"] for entry in data["data"]})

    # -- Internal -------------------------------------------------------------

    def _open(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        request = urllib.request.Request(
            f"{API_BASE}{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            return urllib.request.urlopen(request, timeout=self._timeout)
        except urllib.error.HTTPError as error:
            raise ApiError(error.code, error.read().decode("utf-8", "replace")[:200]) from error
        except TimeoutError as error:
            raise ApiTimeoutError from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, socket.timeout):
                raise ApiTimeoutError from error
            raise NetworkError from error

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with self._open(method, path, payload) as response:
            return json.loads(response.read().decode("utf-8"))
