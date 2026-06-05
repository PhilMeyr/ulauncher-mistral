"""Typed extension exceptions.

Each error carries a language-neutral message key (translated by the UI layer)
and the parameters needed to format it.
"""

from __future__ import annotations


class MistralError(Exception):
    """Base class for all extension errors."""

    message_key: str = "error.unexpected"

    def __init__(self, **params: object) -> None:
        self.params = params
        super().__init__(f"{self.message_key} {params}".strip())


class ApiKeyMissingError(MistralError):
    message_key = "error.api_key_missing"


class ApiError(MistralError):
    """HTTP error returned by the Mistral API."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        keys = {401: "error.api_401", 403: "error.api_403", 429: "error.api_429"}
        self.message_key = keys.get(status, "error.api_http")
        # Only the generic message includes the raw detail returned by the API.
        generic = self.message_key == "error.api_http"
        super().__init__(status=status, detail=detail if generic else "")


class ApiTimeoutError(MistralError):
    message_key = "error.timeout"


class NetworkError(MistralError):
    message_key = "error.network"
