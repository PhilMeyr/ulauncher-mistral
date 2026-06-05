"""Point d'entrée Ulauncher : route les callbacks de l'API v3 vers les commandes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ulauncher.api import Extension
from ulauncher.internals.result import Result

from ui import commands


class MistralExtension(Extension):
    def on_input(self, query_str: str, trigger_id: str) -> list[Result]:
        return commands.suggest(self._context(), query_str)

    def on_item_enter(self, data: Any) -> list[Result]:
        return commands.activate(self._context(), data)

    def _file_preferences(self) -> dict[str, Any]:
        """Préférences relues depuis le fichier de config Ulauncher.

        Contournement : dans v6 beta31 l'app ne notifie pas les extensions des
        changements de préférences (handler `update_preferences` jamais émis), et
        l'env `EXTENSION_PREFERENCES` n'est figé qu'au lancement du processus.
        """
        config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = Path(config_home) / "ulauncher" / "ext_preferences" / f"{self.ext_id}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("preferences", {})
        except (OSError, ValueError):
            return {}

    def _context(self) -> commands.Context:
        """Contexte reconstruit à chaque événement : les préférences sont prises à chaud."""
        prefs = {**self.preferences, **self._file_preferences()}
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
