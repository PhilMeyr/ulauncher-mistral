"""User-facing strings with a light i18n layer.

Note: Ulauncher offers no i18n mechanism for extensions, so manifest.json texts
(preference names/descriptions) stay in English. Everything rendered by the
extension itself (items, errors, confirmations) goes through this module.
Adding a language = adding one entry to _STRINGS and one manifest select option.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "ask.name": 'Ask Mistral: "{question}"',
        "ask.description": "Press Enter to send — model: {model}",
        "help.name": "Type your question after the keyword",
        "help.description": "Subcommands: model (pick the model), reset (clear the history)",
        "answer.header": "Answer ({model}) — press Enter to copy",
        "answer.streaming": "Mistral is answering… ({model})",
        "model.pick.name": "Pick the Mistral model",
        "model.pick.description": "Active model: {model} — press Enter to list models",
        "model.set": "✓ Active model: {model}",
        "reset.name": "Clear the conversation history",
        "reset.description": "Press Enter to start from a blank conversation",
        "reset.done": "✓ Conversation history cleared",
        "error.title": "⚠️ Error",
        "error.open_console": "🔑 Open the Mistral console to create/check an API key",
        "error.retry": "↻ Retry",
        "error.unexpected": "An unexpected error occurred.",
        "error.api_key_missing": "No API key configured. Add it in the extension preferences.",
        "error.api_401": "Invalid or revoked API key. Check it in the preferences.",
        "error.api_403": "Access denied by the Mistral API (key permissions?).",
        "error.api_429": "Rate limit reached. Try again in a few moments.",
        "error.api_http": "The Mistral API returned HTTP error {status}. {detail}",
        "error.timeout": "The Mistral API did not respond in time. Retry or increase the timeout.",
        "error.network": "Could not reach the Mistral API. Check your network connection.",
    },
    "fr": {
        "ask.name": "Demander à Mistral : « {question} »",
        "ask.description": "Entrée pour envoyer — modèle : {model}",
        "help.name": "Tapez votre question après le mot-clé",
        "help.description": "Sous-commandes : model (choix du modèle), reset (vider l'historique)",
        "answer.header": "Réponse ({model}) — Entrée pour copier",
        "answer.streaming": "Mistral répond… ({model})",
        "model.pick.name": "Choisir le modèle Mistral",
        "model.pick.description": "Modèle actif : {model} — Entrée pour lister les modèles",
        "model.set": "✓ Modèle actif : {model}",
        "reset.name": "Vider l'historique de conversation",
        "reset.description": "Entrée pour repartir d'une conversation vierge",
        "reset.done": "✓ Historique de conversation vidé",
        "error.title": "⚠️ Erreur",
        "error.open_console": "🔑 Ouvrir la console Mistral pour créer/vérifier une clé API",
        "error.retry": "↻ Réessayer",
        "error.unexpected": "Une erreur inattendue est survenue.",
        "error.api_key_missing": (
            "Aucune clé API configurée. Ajoutez-la dans les préférences de l'extension."
        ),
        "error.api_401": "Clé API invalide ou révoquée. Vérifiez-la dans les préférences.",
        "error.api_403": "Accès refusé par l'API Mistral (permissions de la clé ?).",
        "error.api_429": "Limite de débit atteinte. Réessayez dans quelques instants.",
        "error.api_http": "L'API Mistral a renvoyé une erreur HTTP {status}. {detail}",
        "error.timeout": (
            "L'API Mistral n'a pas répondu à temps. Réessayez ou augmentez le timeout."
        ),
        "error.network": "Impossible de joindre l'API Mistral. Vérifiez votre connexion réseau.",
    },
}


class Translator:
    """Resolve message keys for a language, falling back to English."""

    def __init__(self, language: str) -> None:
        self._strings = _STRINGS.get(language, _STRINGS[DEFAULT_LANGUAGE])

    def __call__(self, key: str, **params: object) -> str:
        template = self._strings.get(key) or _STRINGS[DEFAULT_LANGUAGE].get(key, key)
        return template.format(**params).strip()
