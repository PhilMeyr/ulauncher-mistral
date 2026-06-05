"""Extension commands (open registries: adding a command = adding a dict entry).

Suggesting (while typing) and activating (on Enter) are segregated into two
registries so a command only implements what it actually does (ISP) — e.g.
"model:set" is activate-only and needs no suggest stub.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Union

from mistral.client import MistralClient
from mistral.conversation import ConversationHistory
from mistral.errors import ApiKeyMissingError, MistralError
from mistral.state import StateStore
from ui import results
from ui.strings import Translator

if TYPE_CHECKING:
    from ulauncher.internals.result import Result

    from mistral.client import Message

logger = logging.getLogger(__name__)

_MODEL_STATE_KEY = "model"
_LAST_ANSWER_STATE_KEY = "last_answer"

#: Generators stream partial result lists when the app supports it (Ulauncher PR pending)
CommandOutput = Union["list[Result]", "Iterator[list[Result]]"]

#: Questions awaiting a Mistral answer — deduplicates double activations
#: (each Ulauncher event runs in its own thread of the same process).
_in_flight: set[str] = set()
_in_flight_lock = threading.Lock()


def _streaming_supported() -> bool:
    return os.environ.get("ULAUNCHER_PARTIAL_RESPONSES") == "1"


@dataclass
class Context:
    """Dependencies and settings injected into commands (built by main.py)."""

    api_key: str
    default_model: str
    system_prompt: str
    history_size: int
    max_tokens: int
    timeout: int
    store: StateStore
    language: str = "en"
    t: Translator = field(init=False)

    def __post_init__(self) -> None:
        self.t = Translator(self.language)

    @property
    def model(self) -> str:
        """Active model: the choice made via the "model" command overrides the preference."""
        return self.store.get(_MODEL_STATE_KEY) or self.default_model

    def client(self) -> MistralClient:
        return MistralClient(self.api_key, timeout=self.timeout)

    def history(self) -> ConversationHistory:
        return ConversationHistory(self.store, self.history_size)


# -- ask ------------------------------------------------------------------


def _suggest_ask(ctx: Context, args: str) -> list[Result]:
    if not ctx.api_key:
        return results.error_results(ctx.t, ApiKeyMissingError())
    if not args:
        return results.help_items(ctx.t)
    return [results.ask_item(ctx.t, args, ctx.model)]


def _activate_ask(ctx: Context, data: dict[str, Any]) -> CommandOutput:
    question = data["query"]
    if not _begin_request(question):
        return results.pending_items(ctx.t)
    if _streaming_supported():
        return _ask_streaming(ctx, question)  # releases the in-flight marker itself
    try:
        answer = ctx.client().chat(
            _build_messages(ctx, question), model=ctx.model, max_tokens=ctx.max_tokens
        )
        _record_answer(ctx, question, answer.content)
        return results.answer_results(ctx.t, answer.content, ctx.model, truncated=answer.truncated)
    finally:
        _end_request(question)


def _ask_streaming(ctx: Context, question: str) -> Iterator[list[Result]]:
    """Yield the growing answer as it streams; errors must be handled here because
    they are raised during iteration, outside the activate() error wrapper."""
    answer = ""
    truncated = False
    retry_data = {"command": "ask", "query": question}
    try:
        try:
            chunks = ctx.client().chat_stream(
                _build_messages(ctx, question), model=ctx.model, max_tokens=ctx.max_tokens
            )
            for chunk in chunks:
                truncated |= chunk.truncated
                if not chunk.delta:  # final finish_reason-only chunk: nothing new to render
                    continue
                answer += chunk.delta
                yield results.answer_results(ctx.t, answer, ctx.model, partial=True)
        except MistralError as error:
            yield results.error_results(ctx.t, error, retry_data=retry_data)
            return
        except Exception:
            logger.exception("Unexpected error while streaming the answer")
            yield results.error_results(ctx.t, MistralError(), retry_data=retry_data)
            return
        _record_answer(ctx, question, answer)
        yield results.answer_results(ctx.t, answer, ctx.model, truncated=truncated)
    finally:
        _end_request(question)


def _build_messages(ctx: Context, question: str) -> list[Message]:
    messages: list[Message] = [{"role": "system", "content": ctx.system_prompt}]
    messages += ctx.history().as_messages()
    messages.append({"role": "user", "content": question})
    return messages


def _record_answer(ctx: Context, question: str, answer: str) -> None:
    """Persist the exchange, and the last answer so "last" can re-display it
    even when Ulauncher drops the response (user typed while waiting)."""
    ctx.history().add_exchange(question, answer)
    ctx.store.set(
        _LAST_ANSWER_STATE_KEY, {"question": question, "answer": answer, "model": ctx.model}
    )


def _begin_request(question: str) -> bool:
    """Register the question as in-flight; False if it already is."""
    with _in_flight_lock:
        if question in _in_flight:
            return False
        _in_flight.add(question)
        return True


def _end_request(question: str) -> None:
    with _in_flight_lock:
        _in_flight.discard(question)


# -- model / reset / last ---------------------------------------------------


def _suggest_model(ctx: Context, args: str) -> list[Result]:
    return [
        results.command_item(
            name=ctx.t("model.pick.name"),
            description=ctx.t("model.pick.description", model=ctx.model),
            data={"command": "model"},
        )
    ]


def _activate_model(ctx: Context, data: dict[str, Any]) -> list[Result]:
    models = ctx.client().list_models()
    return results.model_results(models, ctx.model)


def _activate_set_model(ctx: Context, data: dict[str, Any]) -> list[Result]:
    ctx.store.set(_MODEL_STATE_KEY, data["model"])
    return results.confirmation(ctx.t("model.set", model=data["model"]))


def _suggest_reset(ctx: Context, args: str) -> list[Result]:
    return [
        results.command_item(
            name=ctx.t("reset.name"),
            description=ctx.t("reset.description"),
            data={"command": "reset"},
        )
    ]


def _activate_reset(ctx: Context, data: dict[str, Any]) -> list[Result]:
    ctx.history().clear()
    return results.confirmation(ctx.t("reset.done"))


def _suggest_last(ctx: Context, args: str) -> list[Result]:
    last = ctx.store.get(_LAST_ANSWER_STATE_KEY)
    answer = last.get("answer") if isinstance(last, dict) else None
    if not answer:  # never stored, or corrupted/hand-edited state file
        return results.notice(ctx.t("last.empty"))
    return results.answer_results(ctx.t, answer, last.get("model", ctx.model))


# -- Registries and routers --------------------------------------------------

SuggestFn = Callable[[Context, str], "list[Result]"]
ActivateFn = Callable[[Context, "dict[str, Any]"], CommandOutput]

#: Subcommands reachable by typing their name after the keyword.
SUGGEST: dict[str, SuggestFn] = {
    "model": _suggest_model,
    "reset": _suggest_reset,
    "last": _suggest_last,
}

#: Every activatable command (routed by data["command"] in on_item_enter).
ACTIVATE: dict[str, ActivateFn] = {
    "ask": _activate_ask,
    "model": _activate_model,
    "model:set": _activate_set_model,
    "reset": _activate_reset,
}


def _guarded(
    ctx: Context,
    label: str,
    run: Callable[[], CommandOutput],
    retry_data: dict[str, Any] | None = None,
) -> CommandOutput:
    """Last resort: every exception becomes a visible error item.

    The framework runs both routers in a bare thread with no exception handler,
    so this single wrapper is what guarantees "never a silent failure"."""
    try:
        return run()
    except MistralError as error:
        return results.error_results(ctx.t, error, retry_data=retry_data)
    except Exception:
        logger.exception("Unexpected error while %s", label)
        return results.error_results(ctx.t, MistralError(), retry_data=retry_data)


def _route_suggest(ctx: Context, query: str) -> list[Result]:
    stripped = query.strip()
    subcommand = SUGGEST.get(stripped.lower())
    if subcommand is not None:
        return subcommand(ctx, "")
    return _suggest_ask(ctx, stripped)


def suggest(ctx: Context, query: str) -> list[Result]:
    """Route typed input: exact subcommand match, or a question by default.

    No retry item while typing — the next keystroke re-runs the suggestion."""
    return _guarded(ctx, "suggesting", lambda: _route_suggest(ctx, query))


def activate(ctx: Context, data: dict[str, Any]) -> CommandOutput:
    """Route an activation, with uniform error handling (error item + retry)."""
    handler = ACTIVATE.get(data.get("command", ""))
    if handler is None:
        return results.help_items(ctx.t)
    return _guarded(
        ctx, f"handling {data.get('command')!r}", lambda: handler(ctx, data), retry_data=data
    )
