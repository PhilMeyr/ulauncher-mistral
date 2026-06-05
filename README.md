# ulauncher-mistral

[Ulauncher](https://ulauncher.io) extension to query [Mistral AI](https://mistral.ai) straight from the launcher.

> ⚠️ This extension targets **Ulauncher v6 (beta) / Extension API v3** only. It does not work with Ulauncher 5.x.

## Features

- **`ai <question>`** — ask Mistral a question. Press Enter on "Ask Mistral" to send (no API call while typing). The answer is displayed line by line in Ulauncher (scrollable list); pressing Enter on any line copies the full answer to the clipboard; URLs found in the answer show up as clickable 🔗 items.
- **`ai model`** — lists the available models (fetched live via `GET /v1/models`) and persists your choice. The chosen model overrides the "Default model" preference.
- **`ai reset`** — clears the conversation history.
- **Multi-turn conversation** — the last N exchanges (configurable) are sent back as context with every question.
- **Zero dependencies** — the Mistral API is called with the stdlib (`urllib`), no `pip install` required.

## Installation

1. Install Ulauncher v6 (beta): download the `.deb` from the [releases page](https://github.com/Ulauncher/Ulauncher/releases) then `sudo apt install ./ulauncher_6.0.0.betaXX_all.deb gir1.2-gtklayershell-0.1`.
2. Install the extension:
   ```bash
   ln -s /path/to/ulauncher-mistral \
     ~/.local/share/ulauncher/extensions/com.github.philmeyr.ulauncher-mistral
   ```
   then restart Ulauncher.
3. Create an API key at <https://console.mistral.ai/api-keys> and set it in the extension preferences.

## Preferences

| Preference | Default | Description |
|---|---|---|
| Mistral API key | — | Required |
| Default model | `mistral-small-latest` | Overridden by `ai model` |
| System prompt | "Answer concisely." | Base instructions |
| History size | 4 | Exchanges kept as context (0 = disabled) |
| Max tokens per answer | 1024 | |
| API timeout | 30 s | |

## Known limitations

- **No answer streaming**: Ulauncher's event architecture (including v6 beta31) only allows a single rendered response per activation — the app-side callback is consumed after the first render (`extension_mode.py`). The client (`mistral/client.py`) already exposes `chat_stream()` (SSE), ready to be wired up the day Ulauncher supports progressive rendering.
- Each item is limited to a single line: long answers are split (~90 chars/line) and the list is scrollable.
- Links are not clickable *inside* the text: they are extracted and displayed as dedicated items.
- Preferences are re-read from Ulauncher's config file on every event, as a workaround for a v6 beta31 bug where preference updates are never pushed to running extensions (see the `TODO` in `main.py`).

## Architecture

```
main.py              # MistralExtension: routes Ulauncher callbacks (SRP)
ui/commands.py       # ask/model/reset command registry (OCP) + injected context (DIP)
ui/results.py        # Result factories (DRY)
mistral/client.py    # Mistral REST client (urllib): chat, chat_stream, list_models
mistral/conversation.py  # Sliding window of exchanges
mistral/state.py     # Atomic JSON persistence (XDG_DATA_HOME)
mistral/formatter.py # Line wrapping + URL extraction
mistral/errors.py    # Typed exceptions with user-facing messages
```

The business logic (`mistral/`) never imports Ulauncher; commands depend on the `ChatProvider` protocol, not on the concrete client.

## Development

```bash
ruff check . && ruff format .
# Test without installing:
ulauncher preview /path/to/ulauncher-mistral
```
