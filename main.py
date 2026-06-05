"""Ulauncher entry point: routes API v3 callbacks to the extension commands."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from ulauncher import paths
from ulauncher.api import Extension
from ulauncher.internals.result import Result

from mistral.state import StateStore
from ui import commands

logger = logging.getLogger(__name__)


def _int_pref(prefs: dict[str, Any], key: str, default: int, lo: int, hi: int | None) -> int:
    """Best-effort integer preference, clamped to the manifest bounds.

    A corrupt value (empty string, garbage) falls back to the default instead
    of raising on every keystroke and silently muting the extension."""
    try:
        value = int(prefs.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(lo, value) if hi is None else max(lo, min(hi, value))


def _migrate_legacy_state(new_path: Path) -> None:
    """One-time move of the state file from the pre-0.2 hand-rolled XDG location."""
    data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    legacy = Path(data_home) / "ulauncher-mistral" / "state.json"
    if new_path.exists() or not legacy.exists():
        return
    try:
        new_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.replace(legacy, new_path)
    except OSError:
        logger.warning("Could not migrate legacy state file %s", legacy, exc_info=True)


class MistralExtension(Extension):
    def __init__(self) -> None:
        super().__init__()
        self._prefs_cache: tuple[int, dict[str, Any]] | None = None
        self._state_path = Path(paths.EXTENSIONS_STATE) / f"{self.ext_id}.json"
        _migrate_legacy_state(self._state_path)

    def on_input(self, query_str: str, trigger_id: str) -> list[Result]:
        return commands.suggest(self._context(), query_str)

    def on_item_enter(self, data: Any) -> commands.CommandOutput:
        return commands.activate(self._context(), data)

    def _file_preferences(self) -> dict[str, Any]:
        """Preferences re-read from the Ulauncher config file (mtime-cached).

        TODO: remove this workaround once running Ulauncher >= 6.0.0-beta32.
        In v6.0.0-beta31 the app never notifies extensions of preference changes
        (the `update_preferences` handler in extension_mode.py exists but is never
        emitted), and the EXTENSION_PREFERENCES env var is frozen at process start.
        Fixed upstream on 2026-05-12 by Ulauncher commits eb1e131 ("emit
        update_preferences event after saving user prefs") and 0e80ec3, not yet in
        any release. Once UPDATE_PREFERENCES events are delivered,
        `self.preferences` stays current on its own and this method can be deleted.
        """
        path = Path(paths.EXTENSIONS_CONFIG) / f"{self.ext_id}.json"
        try:
            mtime = path.stat().st_mtime_ns
            if self._prefs_cache is not None and self._prefs_cache[0] == mtime:
                return self._prefs_cache[1]
            prefs = json.loads(path.read_text(encoding="utf-8")).get("preferences", {})
        except (OSError, ValueError):
            return {}
        self._prefs_cache = (mtime, prefs)
        return prefs

    def _context(self) -> commands.Context:
        """Context rebuilt on every event so preference changes apply immediately."""
        prefs = {**self.preferences, **self._file_preferences()}
        return commands.Context(
            api_key=str(prefs.get("api_key", "")).strip(),
            default_model=str(prefs.get("default_model", "mistral-small-latest")),
            system_prompt=str(prefs.get("system_prompt", "Answer concisely.")),
            history_size=_int_pref(prefs, "history_size", 4, 0, 20),
            max_tokens=_int_pref(prefs, "max_tokens", 1024, 1, None),
            timeout=_int_pref(prefs, "timeout", 30, 5, 300),
            store=StateStore(self._state_path),
            language=str(prefs.get("language", "en")),
        )


if __name__ == "__main__":
    MistralExtension().run()
