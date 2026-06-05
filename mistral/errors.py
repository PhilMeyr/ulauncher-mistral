"""Exceptions typées de l'extension, avec un message destiné à l'utilisateur."""

from __future__ import annotations


class MistralError(Exception):
    """Base de toutes les erreurs de l'extension."""

    user_message: str = "Une erreur inattendue est survenue."

    def __init__(self, user_message: str | None = None) -> None:
        if user_message is not None:
            self.user_message = user_message
        super().__init__(self.user_message)


class ApiKeyMissingError(MistralError):
    user_message = "Aucune clé API configurée. Ajoutez-la dans les préférences de l'extension."


class ApiError(MistralError):
    """Erreur HTTP renvoyée par l'API Mistral."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        self.detail = detail
        messages = {
            401: "Clé API invalide ou révoquée. Vérifiez-la dans les préférences.",
            403: "Accès refusé par l'API Mistral (permissions de la clé ?).",
            429: "Limite de débit atteinte. Réessayez dans quelques instants.",
        }
        message = messages.get(status, f"L'API Mistral a renvoyé une erreur HTTP {status}.")
        if detail and status not in messages:
            message = f"{message} {detail}"
        super().__init__(message)


class ApiTimeoutError(MistralError):
    user_message = "L'API Mistral n'a pas répondu à temps. Réessayez ou augmentez le timeout."


class NetworkError(MistralError):
    user_message = "Impossible de joindre l'API Mistral. Vérifiez votre connexion réseau."
