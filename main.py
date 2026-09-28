"""Ulauncher entry point: routes API v3 callbacks to the extension commands."""

from __future__ import annotations

from pathlib import Path

from ulauncher import paths
from ulauncher.api import Extension, Result

from mistral.state import StateStore
from prefs import Preferences, load_specs
from ui import commands


class MistralExtension(Extension):
    def __init__(self) -> None:
        super().__init__()
        self._pref_specs = load_specs()
        self._state_path = Path(paths.EXTENSIONS_STATE) / f"{self.ext_id}.json"

    def on_input(self, query_str: str, trigger_id: str) -> list[Result]:
        return commands.suggest(self._context(), query_str)

    def on_result_activation(self, action_id: str, result: Result) -> commands.CommandOutput:
        return commands.activate(self._context(), action_id, result.get("payload", {}))

    def _context(self) -> commands.Context:
        """Context rebuilt on every event so preference changes apply immediately."""
        prefs = Preferences(self.preferences, self._pref_specs)
        return commands.Context(
            api_key=prefs.text("api_key"),
            default_model=prefs.text("default_model"),
            system_prompt=prefs.text("system_prompt"),
            history_size=prefs.number("history_size"),
            max_tokens=prefs.number("max_tokens"),
            timeout=prefs.number("timeout"),
            store=StateStore(self._state_path),
            copy=self.clipboard_store,
            language=prefs.text("language"),
        )


if __name__ == "__main__":
    MistralExtension().run()
