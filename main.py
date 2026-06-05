"""Ulauncher entry point: routes API v3 callbacks to the extension commands."""

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
        """Preferences re-read from the Ulauncher config file.

        TODO: remove this workaround once Ulauncher fixes live preference updates.
        In v6.0.0-beta31 the app never notifies extensions of preference changes
        (the `update_preferences` handler in extension_mode.py exists but is never
        emitted), and the EXTENSION_PREFERENCES env var is frozen at process start.
        Once UPDATE_PREFERENCES events are actually delivered, `self.preferences`
        will stay current on its own and this method can be deleted.
        """
        config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = Path(config_home) / "ulauncher" / "ext_preferences" / f"{self.ext_id}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("preferences", {})
        except (OSError, ValueError):
            return {}

    def _context(self) -> commands.Context:
        """Context rebuilt on every event so preference changes apply immediately."""
        prefs = {**self.preferences, **self._file_preferences()}
        return commands.Context(
            api_key=str(prefs.get("api_key", "")).strip(),
            default_model=str(prefs.get("default_model", "mistral-small-latest")),
            system_prompt=str(prefs.get("system_prompt", "Answer concisely.")),
            history_size=int(prefs.get("history_size", 4)),
            max_tokens=int(prefs.get("max_tokens", 1024)),
            timeout=int(prefs.get("timeout", 30)),
            language=str(prefs.get("language", "en")),
        )


if __name__ == "__main__":
    MistralExtension().run()
