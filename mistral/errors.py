"""Typed extension exceptions.

Each error carries a language-neutral message key (translated by the UI layer),
the parameters needed to format it, and an optional `help_url` the UI can offer
to open (declarative: the UI never inspects error types or HTTP statuses).
"""

from __future__ import annotations

CONSOLE_API_KEYS_URL = "https://console.mistral.ai/api-keys"


class MistralError(Exception):
    """Base class for all extension errors."""

    message_key: str = "error.unexpected"
    help_url: str | None = None

    def __init__(self, **params: object) -> None:
        self.params = params
        super().__init__(f"{self.message_key} {params}".strip())


class ApiKeyMissingError(MistralError):
    message_key = "error.api_key_missing"
    help_url = CONSOLE_API_KEYS_URL


class ApiError(MistralError):
    """HTTP error returned by the Mistral API."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        keys = {401: "error.api_401", 403: "error.api_403", 429: "error.api_429"}
        self.message_key = keys.get(status, "error.api_http")
        if status == 401:
            self.help_url = CONSOLE_API_KEYS_URL
        # Only the generic message includes the raw detail returned by the API.
        generic = self.message_key == "error.api_http"
        super().__init__(status=status, detail=detail if generic else "")


class ApiResponseError(MistralError):
    """The API answered, but with an unexpected, empty or truncated body."""

    message_key = "error.api_response"


class ApiTimeoutError(MistralError):
    message_key = "error.timeout"


class NetworkError(MistralError):
    message_key = "error.network"
