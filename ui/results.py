"""Centralized `Result` factories (DRY: icons, actions, formatting, translations)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ulauncher.api import Result

from mistral import formatter

if TYPE_CHECKING:
    from mistral.errors import MistralError
    from ui.strings import Translator

ICON = "images/icon.png"

#: Ulauncher renders at most 25 results; keep link items within that budget.
MAX_URL_ITEMS = 5


def _actionable(t: Translator, action_id: str, payload: dict[str, Any], **fields: Any) -> Result:
    """Item routed to `commands.activate(action_id, payload)` on Enter."""
    return Result(
        icon=ICON,
        actions={action_id: {"name": t(f"action.{action_id}")}},
        payload=payload,
        **fields,
    )


def notice(name: str, description: str = "") -> list[Result]:
    """Single informational item with no action."""
    return [Result(name=name, description=description, icon=ICON)]


def ask_item(t: Translator, question: str, model: str) -> Result:
    return _actionable(
        t,
        "ask",
        {"query": question},
        name=t("ask.name", question=question),
        description=t("ask.description", model=model),
    )


def command_item(t: Translator, action_id: str, name: str, description: str) -> Result:
    """Item that triggers a payload-less extension command when activated."""
    return _actionable(t, action_id, {}, name=name, description=description)


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
    copy = {"text": answer}
    results = [
        _actionable(t, "copy", copy, name=t(header_key, model=model)),
        _actionable(t, "copy", copy, compact=True, wrap=True, name=answer),
    ]
    if not partial:
        results.extend(
            _actionable(t, "open", {"url": url}, compact=True, name=f"🔗 {url}")
            for url in formatter.extract_urls(answer)[:MAX_URL_ITEMS]
        )
    if truncated:
        results.extend(notice(t("answer.truncated")))
    return results


def model_results(t: Translator, models: list[str], active: str) -> list[Result]:
    return [
        _actionable(
            t,
            "model:set",
            {"model": model},
            compact=True,
            name=f"{'●' if model == active else '○'} {model}",
        )
        for model in models
    ]


def confirmation(t: Translator, message: str) -> list[Result]:
    return [_actionable(t, "close", {}, name=message)]


def error_results(
    t: Translator,
    error: MistralError,
    retry: tuple[str, dict[str, Any]] | None = None,
) -> list[Result]:
    """Every error becomes a visible item — never a silent failure.

    `retry` is the (action_id, payload) that failed; re-activating it retries."""
    results = [
        Result(name=t("error.title"), description=t(error.message_key, **error.params), icon=ICON)
    ]
    if error.help_url:
        results.append(
            _actionable(
                t, "open", {"url": error.help_url}, compact=True, name=t("error.open_console")
            )
        )
    if retry is not None:
        action_id, payload = retry
        results.append(_actionable(t, action_id, payload, compact=True, name=t("error.retry")))
    return results
