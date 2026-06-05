"""Point d'entrée Ulauncher : route les callbacks de l'API v3 vers les commandes."""

from __future__ import annotations

from typing import Any

from ulauncher.api import Extension
from ulauncher.internals.result import Result

from ui import commands


class MistralExtension(Extension):
    def on_input(self, query_str: str, trigger_id: str) -> list[Result]:
        return commands.suggest(self._context(), query_str)

    def on_item_enter(self, data: Any) -> list[Result]:
        return commands.activate(self._context(), data)

    def _context(self) -> commands.Context:
        """Contexte reconstruit à chaque événement : les préférences sont prises à chaud."""
        prefs = self.preferences
        return commands.Context(
            api_key=str(prefs.get("api_key", "")).strip(),
            default_model=str(prefs.get("default_model", "mistral-small-latest")),
            system_prompt=str(prefs.get("system_prompt", "Réponds de façon concise.")),
            history_size=int(prefs.get("history_size", 4)),
            max_tokens=int(prefs.get("max_tokens", 1024)),
            timeout=int(prefs.get("timeout", 30)),
        )


if __name__ == "__main__":
    MistralExtension().run()
