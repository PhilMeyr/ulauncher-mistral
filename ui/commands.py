"""Extension commands (open registry: adding a command = adding a dict entry)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from mistral.client import MistralClient
from mistral.conversation import ConversationHistory
from mistral.errors import MistralError
from mistral.state import StateStore
from ui import results
from ui.strings import Translator

if TYPE_CHECKING:
    from ulauncher.internals.result import Result

    from mistral.client import ChatProvider, Message

_MODEL_STATE_KEY = "model"


@dataclass
class Context:
    """Dependencies and settings injected into commands (built by main.py)."""

    api_key: str
    default_model: str
    system_prompt: str
    history_size: int
    max_tokens: int
    timeout: int
    language: str = "en"
    store: StateStore = field(default_factory=StateStore)

    @property
    def t(self) -> Translator:
        return Translator(self.language)

    @property
    def model(self) -> str:
        """Active model: the choice made via the "model" command overrides the preference."""
        return self.store.get(_MODEL_STATE_KEY) or self.default_model

    def client(self) -> ChatProvider:
        return MistralClient(self.api_key, timeout=self.timeout)

    def history(self) -> ConversationHistory:
        return ConversationHistory(self.store, self.history_size)


class Command(Protocol):
    """A command suggests items while typing, then executes when activated."""

    def suggest(self, ctx: Context, args: str) -> list[Result]: ...

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]: ...


class AskCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        if not args:
            return results.help_items(ctx.t)
        return [results.ask_item(ctx.t, args, ctx.model)]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        question = data["query"]
        messages: list[Message] = [{"role": "system", "content": ctx.system_prompt}]
        history = ctx.history()
        messages += history.as_messages()
        messages.append({"role": "user", "content": question})
        answer = ctx.client().chat(messages, model=ctx.model, max_tokens=ctx.max_tokens)
        history.add_exchange(question, answer)
        return results.answer_results(ctx.t, answer, ctx.model)


class ModelCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        return [
            results.command_item(
                name=ctx.t("model.pick.name"),
                description=ctx.t("model.pick.description", model=ctx.model),
                data={"command": "model"},
            )
        ]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        models = ctx.client().list_models()
        return results.model_results(models, ctx.model)


class SetModelCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:  # never suggested directly
        return []

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        ctx.store.set(_MODEL_STATE_KEY, data["model"])
        return results.confirmation(ctx.t("model.set", model=data["model"]))


class ResetCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        return [
            results.command_item(
                name=ctx.t("reset.name"),
                description=ctx.t("reset.description"),
                data={"command": "reset"},
            )
        ]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        ctx.history().clear()
        return results.confirmation(ctx.t("reset.done"))


#: Subcommands reachable by typing their name after the keyword.
SUBCOMMANDS: dict[str, Command] = {
    "model": ModelCommand(),
    "reset": ResetCommand(),
}

#: Every activatable command (routed by data["command"] in on_item_enter).
COMMANDS: dict[str, Command] = {
    "ask": AskCommand(),
    "model:set": SetModelCommand(),
    **SUBCOMMANDS,
}

DEFAULT_COMMAND: Command = COMMANDS["ask"]


def suggest(ctx: Context, query: str) -> list[Result]:
    """Route typed input: exact subcommand match, or a question by default."""
    stripped = query.strip()
    command = SUBCOMMANDS.get(stripped.lower())
    if command is not None:
        return command.suggest(ctx, "")
    return DEFAULT_COMMAND.suggest(ctx, stripped)


def activate(ctx: Context, data: dict[str, Any]) -> list[Result]:
    """Route an activation, with uniform error handling (error item + retry)."""
    command = COMMANDS.get(data.get("command", ""))
    if command is None:
        return results.help_items(ctx.t)
    try:
        return command.activate(ctx, data)
    except MistralError as error:
        return results.error_results(ctx.t, error, retry_data=data)
