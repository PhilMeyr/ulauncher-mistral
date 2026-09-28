# ulauncher-mistral

[Ulauncher](https://ulauncher.io) extension to query [Mistral AI](https://mistral.ai) straight from the launcher.

> ⚠️ Requires **Ulauncher ≥ 6.0.0-beta35** (Extension API v3). It does not work with Ulauncher 5.x or earlier v6 betas.

## Features

- **`ai <question>`** — ask Mistral a question. Press Enter on "Ask Mistral" to send (no API call while typing). The answer streams in as it is generated and is rendered as a wrapped item; pressing Enter copies the full answer to the clipboard; URLs found in the answer show up as clickable 🔗 items (after the answer body).
- **`ai model`** — lists the available models (fetched live via `GET /v1/models`) and persists your choice. The chosen model overrides the "Default model" preference.
- **`ai reset`** — clears the conversation history.
- **`ai last`** — shows the last answer again (handy if Ulauncher dropped the rendered answer because you typed while waiting).
- **Multi-turn conversation** — the last N exchanges (configurable) are sent back as context with every question.
- **Zero dependencies** — the Mistral API is called with the stdlib (`urllib`), no `pip install` required.
- **Localized interface** — the items and error messages rendered by the extension are available in English and French ("Interface language" preference). Adding a language = one entry in `ui/strings.py` + one option in `manifest.json`. Note: the preference names in `manifest.json` itself cannot be localized (Ulauncher has no i18n mechanism for extensions).

## Installation

1. Install Ulauncher v6: go to the [official download page](https://ulauncher.io/#Download), select **v6**, and run the command recommended for your distribution.
2. Install the extension: open Ulauncher **Preferences → Extensions → Add extension**, then paste this repository's URL:
   ```
   https://github.com/PhilMeyr/ulauncher-mistral
   ```
3. Create an API key at <https://console.mistral.ai/api-keys> and set it in the extension preferences.

## Preferences

| Preference | Default | Description |
|---|---|---|
| Interface language | English | Language of the extension's items/messages (en/fr) |
| Mistral API key | — | Required |
| Default model | `mistral-small-latest` | Overridden by `ai model` |
| System prompt | "Answer concisely." | Base instructions |
| History size | 4 | Exchanges kept as context (0 = disabled) |
| Max tokens per answer | 1024 | |
| API timeout | 30 s | |

## Known limitations

- Links are not clickable *inside* the text: they are extracted and displayed as dedicated items (capped at 5, Ulauncher renders at most 25 results).

## Privacy & security notes

- The API key is stored **in plain text** by Ulauncher itself in `~/.config/ulauncher/ext_preferences/` (platform behaviour — the extension never logs or displays it).
- The conversation history and the last answer are persisted **in plain text** in Ulauncher's extension state directory (`$XDG_STATE_HOME/ulauncher/ext_state/`, file written with mode `0600`). Run `ai reset` to clear the history.
- URLs found in answers come from LLM output and are therefore untrusted: only `http(s)` URLs are offered, URLs embedding userinfo (`https://trusted@evil`) are dropped, and the full URL is always shown in the item label before you open it.

## Architecture

```
main.py              # MistralExtension: routes Ulauncher callbacks (SRP)
prefs.py             # Typed preferences, defaults and bounds read from manifest.json
ui/commands.py       # SUGGEST + ACTIVATE registries, keyed by result action id (OCP, ISP)
ui/results.py        # Result factories: one action + payload per item (DRY)
mistral/client.py    # Mistral REST client (urllib): chat_stream (SSE), list_models
mistral/conversation.py  # Sliding window of exchanges
mistral/state.py     # Atomic, thread-safe JSON persistence (mtime-cached)
mistral/formatter.py # Safe URL extraction from answers
ui/strings.py        # Light i18n layer (en/fr) for all user-facing strings
mistral/errors.py    # Typed exceptions carrying language-neutral message keys
```

The business logic (`mistral/`) never imports Ulauncher. Every transport or parsing failure is translated into a typed `MistralError` at the client boundary, and the command router has a last-resort handler — an error is always rendered as a visible item, never a silent failure.

## Development

```bash
ruff check . && ruff format .
python3 -m unittest    # stdlib only; tests/_stubs stands in for the ulauncher package
# Test without installing:
ulauncher preview /path/to/ulauncher-mistral
```
