"""Persistance JSON de l'état de l'extension (modèle choisi, historique de conversation)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _default_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return Path(data_home) / "ulauncher-mistral" / "state.json"


class StateStore:
    """Petit magasin clé/valeur persisté en JSON, avec écriture atomique."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_path()

    def get(self, key: str, default: Any = None) -> Any:
        return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._save(data)

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except BaseException:
            os.unlink(tmp_path)
            raise
