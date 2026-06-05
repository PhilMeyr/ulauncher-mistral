"""Commandes de l'extension (registre ouvert : en ajouter une = une entrée de dict)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from ulauncher.internals.result import Result

from mistral.client import MistralClient
from mistral.conversation import ConversationHistory
from mistral.errors import MistralError
from mistral.state import StateStore
from ui import results

if TYPE_CHECKING:
    from mistral.client import ChatProvider, Message

_MODEL_STATE_KEY = "model"


@dataclass
class Context:
    """Dépendances et réglages injectés dans les commandes (construits par main.py)."""

    api_key: str
    default_model: str
    system_prompt: str
    history_size: int
    max_tokens: int
    timeout: int
    store: StateStore = field(default_factory=StateStore)

    @property
    def model(self) -> str:
        """Modèle actif : le choix fait via « model » prime sur la préférence."""
        return self.store.get(_MODEL_STATE_KEY) or self.default_model

    def client(self) -> ChatProvider:
        return MistralClient(self.api_key, timeout=self.timeout)

    def history(self) -> ConversationHistory:
        return ConversationHistory(self.store, self.history_size)


class Command(Protocol):
    """Une commande propose des items pendant la frappe puis s'exécute à l'activation."""

    def suggest(self, ctx: Context, args: str) -> list[Result]: ...

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]: ...


class AskCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        if not args:
            return results.help_items()
        return [results.ask_item(args, ctx.model)]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        question = data["query"]
        messages: list[Message] = [{"role": "system", "content": ctx.system_prompt}]
        history = ctx.history()
        messages += history.as_messages()
        messages.append({"role": "user", "content": question})
        answer = ctx.client().chat(messages, model=ctx.model, max_tokens=ctx.max_tokens)
        history.add_exchange(question, answer)
        return results.answer_results(answer, ctx.model)


class ModelCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        return [
            results.command_item(
                name="Choisir le modèle Mistral",
                description=f"Modèle actif : {ctx.model} — Entrée pour lister les modèles",
                data={"command": "model"},
            )
        ]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        models = ctx.client().list_models()
        return results.model_results(models, ctx.model)


class SetModelCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:  # jamais suggérée directement
        return []

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        ctx.store.set(_MODEL_STATE_KEY, data["model"])
        return results.confirmation(f"✓ Modèle actif : {data['model']}")


class ResetCommand:
    def suggest(self, ctx: Context, args: str) -> list[Result]:
        return [
            results.command_item(
                name="Vider l'historique de conversation",
                description="Entrée pour repartir d'une conversation vierge",
                data={"command": "reset"},
            )
        ]

    def activate(self, ctx: Context, data: dict[str, Any]) -> list[Result]:
        ctx.history().clear()
        return results.confirmation("✓ Historique de conversation vidé")


#: Sous-commandes accessibles en tapant leur nom après le mot-clé.
SUBCOMMANDS: dict[str, Command] = {
    "model": ModelCommand(),
    "reset": ResetCommand(),
}

#: Toutes les commandes activables (routées par data["command"] dans on_item_enter).
COMMANDS: dict[str, Command] = {
    "ask": AskCommand(),
    "model:set": SetModelCommand(),
    **SUBCOMMANDS,
}

DEFAULT_COMMAND: Command = COMMANDS["ask"]


def suggest(ctx: Context, query: str) -> list[Result]:
    """Routage de la frappe : sous-commande exacte ou question par défaut."""
    stripped = query.strip()
    command = SUBCOMMANDS.get(stripped.lower())
    if command is not None:
        return command.suggest(ctx, "")
    return DEFAULT_COMMAND.suggest(ctx, stripped)


def activate(ctx: Context, data: dict[str, Any]) -> list[Result]:
    """Routage d'une activation, avec gestion d'erreurs uniforme (item + réessayer)."""
    command = COMMANDS.get(data.get("command", ""))
    if command is None:
        return results.help_items()
    try:
        return command.activate(ctx, data)
    except MistralError as error:
        return results.error_results(error, retry_data=data)
