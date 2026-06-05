"""JSON persistence of the extension state (chosen model, conversation history)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import TYPE_CHECKING, Any, Callable, ClassVar

if TYPE_CHECKING:
    from pathlib import Path


class StateStore:
    """Small key/value store persisted as JSON, with atomic writes.

    Thread-safe: Ulauncher runs every event in its own thread and instances are
    rebuilt per event, so both the parsed-content cache (invalidated by file
    mtime — no disk read per keystroke) and the lock serializing every
    read-modify-write live at class level, shared across instances.
    """

    _lock = threading.Lock()
    #: path -> (st_mtime_ns, parsed content). Values are shared: never mutate them.
    _cache: ClassVar[dict[Path, tuple[int, dict[str, Any]]]] = {}

    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.update(key, lambda _current: value)

    def update(self, key: str, fn: Callable[[Any], Any]) -> None:
        """Atomically replace the value of `key` with `fn(current_value)`.

        `fn` receives the current value (or None) and must return a *new* value
        rather than mutating the one it received (it may be the cached object).
        """
        with self._lock:
            data = dict(self._load())
            data[key] = fn(data.get(key))
            self._save(data)

    def _load(self) -> dict[str, Any]:
        # Caller must hold _lock.
        try:
            mtime = self._path.stat().st_mtime_ns
        except OSError:
            return {}
        cached = StateStore._cache.get(self._path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        StateStore._cache[self._path] = (mtime, data)
        return data

    def _save(self, data: dict[str, Any]) -> None:
        # Caller must hold _lock. 0o700: the conversation history is plain text.
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except BaseException:
            os.unlink(tmp_path)
            raise
        StateStore._cache[self._path] = (self._path.stat().st_mtime_ns, data)
