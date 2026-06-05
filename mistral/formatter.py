"""Mise en forme des réponses pour l'affichage en items Ulauncher (une ligne par item)."""

from __future__ import annotations

import re
import textwrap

LINE_WIDTH = 90

# URLs http(s), en excluant la ponctuation finale et les fermetures markdown.
_URL_PATTERN = re.compile(r"https?://[^\s<>\)\]]+")


def wrap_lines(text: str, width: int = LINE_WIDTH) -> list[str]:
    """Découpe le texte en lignes courtes en respectant mots et paragraphes."""
    lines: list[str] = []
    for paragraph in text.splitlines():
        stripped = paragraph.strip()
        if not stripped:
            continue
        lines.extend(textwrap.wrap(stripped, width=width) or [stripped])
    return lines


def extract_urls(text: str) -> list[str]:
    """URLs uniques trouvées dans la réponse, dans leur ordre d'apparition."""
    urls: list[str] = []
    for match in _URL_PATTERN.findall(text):
        url = match.rstrip(".,;:!?'\"")
        if url not in urls:
            urls.append(url)
    return urls
