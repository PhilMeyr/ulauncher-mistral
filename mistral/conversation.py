"""Historique de conversation multi-tours, persisté via StateStore."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mistral.client import Message
    from mistral.state import StateStore

_STATE_KEY = "history"


class ConversationHistory:
    """Fenêtre glissante des derniers échanges, envoyée comme contexte à Mistral."""

    def __init__(self, store: StateStore, max_exchanges: int) -> None:
        self._store = store
        self._max_exchanges = max_exchanges

    def as_messages(self) -> list[Message]:
        """Messages user/assistant des N derniers échanges, prêts pour l'API."""
        if self._max_exchanges <= 0:
            return []
        exchanges: list[list[str]] = self._store.get(_STATE_KEY, [])
        messages: list[Message] = []
        for question, answer in exchanges[-self._max_exchanges :]:
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": answer})
        return messages

    def add_exchange(self, question: str, answer: str) -> None:
        if self._max_exchanges <= 0:
            return
        exchanges: list[list[str]] = self._store.get(_STATE_KEY, [])
        exchanges.append([question, answer])
        self._store.set(_STATE_KEY, exchanges[-self._max_exchanges :])

    def clear(self) -> None:
        self._store.set(_STATE_KEY, [])
