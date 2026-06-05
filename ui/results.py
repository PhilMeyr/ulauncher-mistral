"""Centralized `Result` factories (DRY: icons, actions, formatting, translations)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.internals import effects
from ulauncher.internals.result import Result

from mistral import formatter

if TYPE_CHECKING:
    from mistral.errors import MistralError
    from ui.strings import Translator

ICON = "images/icon.png"

#: Ulauncher renders at most 25 results; keep link items within that budget.
MAX_URL_ITEMS = 5


def _copy_effect(text: str) -> dict[str, Any]:
    """Copy-to-clipboard effect (legacy format, still supported in API v3)."""
    return {"type": "effect:legacy_copy", "data": text}


def notice(name: str, description: str = "") -> list[Result]:
    """Single informational item with no action."""
    return [Result(name=name, description=description, icon=ICON)]


def ask_item(t: Translator, question: str, model: str) -> Result:
    return command_item(
        name=t("ask.name", question=question),
        description=t("ask.description", model=model),
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


def help_items(t: Translator) -> list[Result]:
    return notice(t("help.name"), t("help.description"))


def pending_items(t: Translator) -> list[Result]:
    """Shown when the same question is already waiting for an answer."""
    return notice(t("ask.pending"), t("ask.pending.description"))


def answer_results(
    t: Translator, answer: str, model: str, partial: bool = False, truncated: bool = False
) -> list[Result]:
    """Full answer: copyable header, wrapped body, then clickable links (final only)."""
    header_key = "answer.streaming" if partial else "answer.header"
    results = [
        Result(
            name=t(header_key, model=model),
            icon=ICON,
            on_enter=_copy_effect(answer),
        ),
        # wrap needs the app-side Result.wrap support; older apps render one ellipsized line
        Result(compact=True, wrap=True, name=answer, icon=ICON, on_enter=_copy_effect(answer)),
    ]
    if not partial:
        results.extend(
            Result(
                compact=True,
                name=f"🔗 {url}",
                icon=ICON,
                on_enter=effects.open(url),
            )
            for url in formatter.extract_urls(answer)[:MAX_URL_ITEMS]
        )
    if truncated:
        results.extend(notice(t("answer.truncated")))
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


def error_results(
    t: Translator, error: MistralError, retry_data: dict[str, Any] | None = None
) -> list[Result]:
    """Every error becomes a visible item — never a silent failure."""
    results = [
        Result(name=t("error.title"), description=t(error.message_key, **error.params), icon=ICON)
    ]
    if error.help_url:
        results.append(
            Result(
                compact=True,
                name=t("error.open_console"),
                icon=ICON,
                on_enter=effects.open(error.help_url),
            )
        )
    if retry_data is not None:
        results.append(
            Result(
                compact=True,
                name=t("error.retry"),
                icon=ICON,
                on_enter=ExtensionCustomAction(retry_data, keep_app_open=True),
            )
        )
    return results
