"""Formatting of answers for display as Ulauncher items (one line per item)."""

from __future__ import annotations

import re
import textwrap

LINE_WIDTH = 90

# http(s) URLs, excluding trailing punctuation and markdown closers.
_URL_PATTERN = re.compile(r"https?://[^\s<>\)\]]+")


def wrap_lines(text: str, width: int = LINE_WIDTH) -> list[str]:
    """Split the text into short lines, preserving words and paragraphs."""
    lines: list[str] = []
    for paragraph in text.splitlines():
        stripped = paragraph.strip()
        if not stripped:
            continue
        lines.extend(textwrap.wrap(stripped, width=width) or [stripped])
    return lines


def extract_urls(text: str) -> list[str]:
    """Unique URLs found in the answer, in order of appearance."""
    urls: list[str] = []
    for match in _URL_PATTERN.findall(text):
        url = match.rstrip(".,;:!?'\"")
        if url not in urls:
            urls.append(url)
    return urls
