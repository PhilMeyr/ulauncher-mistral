"""Extraction of safe, clickable URLs from answers (LLM output is untrusted)."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

# Broad http(s) match: trailing prose punctuation and markdown/bracket closers
# are trimmed afterwards by _clean_url, so URLs may legitimately contain ()
# and [] (e.g. https://en.wikipedia.org/wiki/Python_(programming_language)).
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")

_TRAILING_PUNCTUATION = ".,;:!?'\""
_BRACKET_PAIRS = {")": "(", "]": "["}


def extract_urls(text: str) -> list[str]:
    """Unique safe URLs found in the answer, in order of appearance."""
    cleaned = (_clean_url(match) for match in _URL_PATTERN.findall(text))
    return list(dict.fromkeys(url for url in cleaned if url and _is_safe(url)))


def _clean_url(url: str) -> str:
    """Trim trailing prose punctuation and unbalanced closing brackets."""
    url = url.rstrip(_TRAILING_PUNCTUATION)
    while url and url[-1] in _BRACKET_PAIRS:
        closer = url[-1]
        if url.count(_BRACKET_PAIRS[closer]) >= url.count(closer):
            break  # balanced: the bracket belongs to the URL
        url = url[:-1].rstrip(_TRAILING_PUNCTUATION)
    return url


def _is_safe(url: str) -> bool:
    """Reject URLs whose authority embeds userinfo: the displayed label of
    "https://trusted.com@evil.tld" would be misleading, and the LLM that
    produced the URL is not a trusted source."""
    try:
        return "@" not in urlsplit(url).netloc
    except ValueError:
        return False
