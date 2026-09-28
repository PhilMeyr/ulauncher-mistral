"""Typed preference values, with defaults and bounds read from manifest.json (single source)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"


def load_specs(manifest_path: Path = MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))["preferences"]


class Preferences:
    """Read-only view over the raw preferences dict pushed by Ulauncher."""

    def __init__(self, raw: dict[str, Any], specs: dict[str, dict[str, Any]]) -> None:
        self._raw = raw
        self._specs = specs

    def text(self, key: str) -> str:
        value = self._raw.get(key)
        return str(self._specs[key].get("default_value", "") if value is None else value).strip()

    def number(self, key: str) -> int:
        """Integer clamped to the manifest bounds.

        A corrupt value (empty string, garbage) falls back to the default instead
        of raising on every keystroke and silently muting the extension."""
        spec = self._specs[key]
        try:
            value = int(self._raw.get(key, spec["default_value"]))
        except (TypeError, ValueError):
            return int(spec["default_value"])
        value = max(spec.get("min", value), value)
        return min(spec.get("max", value), value)
