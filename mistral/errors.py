"""Typed extension exceptions, each carrying a user-facing message."""

from __future__ import annotations


class MistralError(Exception):
    """Base class for all extension errors."""

    user_message: str = "An unexpected error occurred."

    def __init__(self, user_message: str | None = None) -> None:
        if user_message is not None:
            self.user_message = user_message
        super().__init__(self.user_message)


class ApiKeyMissingError(MistralError):
    user_message = "No API key configured. Add it in the extension preferences."


class ApiError(MistralError):
    """HTTP error returned by the Mistral API."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        self.detail = detail
        messages = {
            401: "Invalid or revoked API key. Check it in the preferences.",
            403: "Access denied by the Mistral API (key permissions?).",
            429: "Rate limit reached. Try again in a few moments.",
        }
        message = messages.get(status, f"The Mistral API returned HTTP error {status}.")
        if detail and status not in messages:
            message = f"{message} {detail}"
        super().__init__(message)


class ApiTimeoutError(MistralError):
    user_message = "The Mistral API did not respond in time. Retry or increase the timeout."


class NetworkError(MistralError):
    user_message = "Could not reach the Mistral API. Check your network connection."
