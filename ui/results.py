"""Fabriques centralisées de `Result` Ulauncher (DRY : icônes, actions, mise en forme)."""

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
    """Effet « copier dans le presse-papiers » (format legacy, toujours supporté en v3)."""
    return {"type": "effect:legacy_copy", "data": text}


def ask_item(question: str, model: str) -> Result:
    return command_item(
        name=f"Demander à Mistral : « {question} »",
        description=f"Entrée pour envoyer — modèle : {model}",
        data={"command": "ask", "query": question},
    )


def command_item(name: str, description: str, data: dict[str, Any]) -> Result:
    """Item qui déclenche une commande de l'extension à l'activation."""
    return Result(
        name=name,
        description=description,
        icon=ICON,
        on_enter=ExtensionCustomAction(data, keep_app_open=True),
    )


def help_items() -> list[Result]:
    return [
        Result(
            name="Posez votre question après le mot-clé",
            description="Sous-commandes : model (choix du modèle), reset (vider l'historique)",
            icon=ICON,
        ),
    ]


def answer_results(answer: str, model: str) -> list[Result]:
    """Réponse complète : en-tête copiable, corps ligne par ligne, liens cliquables."""
    results = [
        Result(
            name=f"Réponse ({model}) — Entrée pour copier",
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
    """Toute erreur devient un item visible, jamais d'échec silencieux."""
    results = [Result(name="⚠️ Erreur", description=error.user_message, icon=ICON)]
    if isinstance(error, ApiKeyMissingError) or (
        isinstance(error, ApiError) and error.status == 401
    ):
        results.append(
            Result(
                compact=True,
                name="🔑 Ouvrir la console Mistral pour créer/vérifier une clé API",
                icon=ICON,
                on_enter=effects.open(_API_KEYS_URL),
            )
        )
    if retry_data is not None:
        results.append(
            Result(
                compact=True,
                name="↻ Réessayer",
                icon=ICON,
                on_enter=ExtensionCustomAction(retry_data, keep_app_open=True),
            )
        )
    return results
