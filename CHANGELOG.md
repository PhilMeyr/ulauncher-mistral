# Changelog

## [0.2.0] - 2026-09-29

### Breaking

- Requires Ulauncher 6.0.0-beta35 or later (#7)
- Requires Python 3.9 or later; `pyproject.toml` no longer claims 3.8 support (#5)

### Added

- `ai last` re-displays the last answer, which Ulauncher drops when the user types while waiting (#4)
- Answers always stream, using the native generator handlers (#7)
- Missing API key is detected while typing (#4)
- Notice when an answer is cut off by `max_tokens`, also in streaming mode (#4, #5)
- Unit tests (stdlib `unittest`) and a GitHub Actions workflow running ruff and the tests on Python 3.9 and 3.14 (#7)

### Changed

- Preferences come from Ulauncher's live updates; the config-file re-read workaround is gone (#7)
- `on_enter` / `ExtensionCustomAction` replaced by `Result.actions` + `on_result_activation` (#7)
- `max_tokens` preference declares `max: 32768`; Ulauncher capped it at 100 otherwise (#6)
- Numeric preferences are clamped to the manifest bounds (#4)
- State file: process-wide lock, atomic updates and mtime cache (#4)
- Double Enter no longer fires a second billed API call (#4)
- URL extraction keeps legitimate parentheses, drops URLs embedding userinfo and caps link items at 5, listed after the answer (#4)

### Fixed

- Read timeouts and truncated responses no longer kill the Ulauncher event thread; every failure renders a visible error item (#4, #5)
- Exceptions raised while typing (e.g. corrupted state file) no longer fail silently (#5)
- Empty answers no longer pollute the conversation history (#4)

### Removed

- Non-streaming `chat()` path and the `ULAUNCHER_PARTIAL_RESPONSES` switch (#7)
- Legacy state-file migration (#7)

## [0.1.0] - 2026-06-05

First public release: `ai <question>`, `ai model`, `ai reset`, multi-turn context, English/French interface, no third-party dependencies.
