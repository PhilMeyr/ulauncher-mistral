from types import SimpleNamespace


class Result(dict):
    def __init__(self, **fields):
        super().__init__(**fields)


class Extension:
    pass


effects = SimpleNamespace(
    open=lambda url: {"type": "effect:open", "data": url},
    close_window=lambda: {"type": "effect:close_window"},
)
