"""Centralized `Result` factories (DRY: icons, actions, formatting)."""

from __future__ import annotations

from typing import Any

from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.internals import effects
from ulauncher.internals.result import Result

from mistral import formatter
from mistral.errors import ApiError, ApiKeyMissingError, MistralError

ICON = "images/icon.png"

_API_KEYS_URL = "https://console.mistral.ai/api-keys"


def _copy_effect(text: str) -> dict[str, Any]:
    """Copy-to-clipboard effect (legacy format, still supported in API v3)."""
    return {"type": "effect:legacy_copy", "data": text}


def ask_item(question: str, model: str) -> Result:
    return command_item(
        name=f'Ask Mistral: "{question}"',
        description=f"Press Enter to send — model: {model}",
        data={"command": "ask", "query": question},
    )


def command_item(name: str, description: str, data: dict[str, Any]) -> Result:
    """Item that triggers an extension command when activated."""
    return Result(
        name=name,
        description=description,
        icon=ICON,
        on_enter=ExtensionCustomAction(data, keep_app_open=True),
    )


def help_items() -> list[Result]:
    return [
        Result(
            name="Type your question after the keyword",
            description="Subcommands: model (pick the model), reset (clear the history)",
            icon=ICON,
        ),
    ]


def answer_results(answer: str, model: str) -> list[Result]:
    """Full answer: copyable header, body line by line, clickable links."""
    results = [
        Result(
            name=f"Answer ({model}) — press Enter to copy",
            icon=ICON,
            on_enter=_copy_effect(answer),
        )
    ]
    results.extend(
        Result(compact=True, name=line, icon=ICON, on_enter=_copy_effect(answer))
        for line in formatter.wrap_lines(answer)
    )
    results.extend(
        Result(
            compact=True,
            name=f"🔗 {url}",
            icon=ICON,
            on_enter=effects.open(url),
        )
        for url in formatter.extract_urls(answer)
    )
    return results


def model_results(models: list[str], active: str) -> list[Result]:
    return [
        Result(
            compact=True,
            name=f"{'●' if model == active else '○'} {model}",
            icon=ICON,
            on_enter=ExtensionCustomAction(
                {"command": "model:set", "model": model}, keep_app_open=True
            ),
        )
        for model in models
    ]


def confirmation(message: str) -> list[Result]:
    return [Result(name=message, icon=ICON, on_enter=effects.close_window())]


def error_results(error: MistralError, retry_data: dict[str, Any] | None = None) -> list[Result]:
    """Every error becomes a visible item — never a silent failure."""
    results = [Result(name="⚠️ Error", description=error.user_message, icon=ICON)]
    if isinstance(error, ApiKeyMissingError) or (
        isinstance(error, ApiError) and error.status == 401
    ):
        results.append(
            Result(
                compact=True,
                name="🔑 Open the Mistral console to create/check an API key",
                icon=ICON,
                on_enter=effects.open(_API_KEYS_URL),
            )
        )
    if retry_data is not None:
        results.append(
            Result(
                compact=True,
                name="↻ Retry",
                icon=ICON,
                on_enter=ExtensionCustomAction(retry_data, keep_app_open=True),
            )
        )
    return results
