"""Minimal HTTP client for the Mistral API (stdlib only, zero dependencies)."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, NamedTuple

from mistral.errors import (
    ApiError,
    ApiKeyMissingError,
    ApiResponseError,
    ApiTimeoutError,
    MistralError,
    NetworkError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

API_BASE = "https://api.mistral.ai/v1"

Message = dict[str, str]  # {"role": ..., "content": ...}


class ChatAnswer(NamedTuple):
    """Answer returned by `chat`, with the truncation fact the UI may surface."""

    content: str
    truncated: bool  # the API stopped at max_tokens (finish_reason == "length")


class StreamChunk(NamedTuple):
    """One SSE chunk from `chat_stream`; `truncated` mirrors `ChatAnswer.truncated`."""

    delta: str
    truncated: bool  # this chunk carried finish_reason == "length"


@contextmanager
def _translating_errors() -> Iterator[None]:
    """Single point translating every transport/parsing failure into a MistralError.

    Must wrap *all* network I/O and response decoding — including body reads and
    JSON parsing, which can fail long after the connection was opened — so that
    no raw exception ever escapes to the (unprotected) Ulauncher event thread.
    """
    try:
        yield
    except MistralError:
        raise
    except urllib.error.HTTPError as error:
        raise ApiError(error.code, error.read().decode("utf-8", "replace")[:200]) from error
    except TimeoutError as error:
        raise ApiTimeoutError from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, socket.timeout):
            raise ApiTimeoutError from error
        raise NetworkError from error
    except OSError as error:
        raise NetworkError from error
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
        # json.JSONDecodeError / UnicodeDecodeError are ValueError; the lookup
        # errors cover responses missing the expected structure.
        raise ApiResponseError from error


class MistralClient:
    """Mistral REST API client on top of urllib."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        if not api_key:
            raise ApiKeyMissingError
        self._api_key = api_key
        self._timeout = timeout

    # -- Public API ---------------------------------------------------------

    def chat(self, messages: list[Message], model: str, max_tokens: int) -> ChatAnswer:
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        data = self._request_json("POST", "/chat/completions", payload)
        with _translating_errors():
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        if not content:
            raise ApiResponseError
        return ChatAnswer(content=content, truncated=finish_reason == "length")

    def chat_stream(
        self, messages: list[Message], model: str, max_tokens: int
    ) -> Iterator[StreamChunk]:
        """Iterate over the text deltas returned as SSE (`stream: true`).

        The final SSE chunk usually carries `finish_reason` with no content; it is
        yielded too (empty delta) so the truncation fact reaches the caller."""
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True}
        with _translating_errors(), self._open("POST", "/chat/completions", payload) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:") :].strip()
                if chunk == "[DONE]":
                    break
                choice = json.loads(chunk)["choices"][0]
                delta = choice["delta"].get("content")
                finish_reason = choice.get("finish_reason")
                if delta or finish_reason:
                    yield StreamChunk(delta=delta or "", truncated=finish_reason == "length")

    def list_models(self) -> list[str]:
        data = self._request_json("GET", "/models")
        with _translating_errors():
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
        with _translating_errors():
            return urllib.request.urlopen(request, timeout=self._timeout)

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with _translating_errors(), self._open(method, path, payload) as response:
            return json.loads(response.read().decode("utf-8"))
