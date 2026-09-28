import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mistral.client import StreamChunk
from mistral.errors import ApiTimeoutError
from mistral.state import StateStore
from ui import commands


def _actions(items):
    return [next(iter(item.get("actions", {})), None) for item in items]


class CommandsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.copied = []
        self.ctx = self._context(api_key="key")
        self.store_path = Path(tmp.name) / "state.json"
        self.ctx.store = StateStore(self.store_path)
        patcher = mock.patch.object(commands, "MistralClient")
        self.client = patcher.start().return_value
        self.addCleanup(patcher.stop)

    def _context(self, api_key):
        return commands.Context(
            api_key=api_key,
            default_model="small",
            system_prompt="Be brief.",
            history_size=4,
            max_tokens=100,
            timeout=30,
            store=None,
            copy=self.copied.append,
        )

    def test_suggest_routes_subcommands_and_questions(self):
        self.assertEqual(_actions(commands.suggest(self.ctx, " Model ")), ["model"])
        [ask] = commands.suggest(self.ctx, "why?")
        self.assertEqual(ask["payload"], {"query": "why?"})
        self.assertEqual(_actions(commands.suggest(self.ctx, "")), [None])

    def test_suggest_without_api_key_offers_the_console(self):
        items = commands.suggest(self._context(api_key=""), "why?")
        self.assertEqual(_actions(items), [None, "open"])

    def test_ask_streams_then_records_the_answer(self):
        self.client.chat_stream.return_value = iter(
            [StreamChunk("Hi ", False), StreamChunk("https://a.fr", False), StreamChunk("", True)]
        )
        batches = list(commands.activate(self.ctx, "ask", {"query": "q"}))

        self.assertEqual(len(batches), 3)
        final = batches[-1]
        self.assertEqual(_actions(final), ["copy", "copy", "open", None])
        self.assertEqual(final[0]["payload"], {"text": "Hi https://a.fr"})
        self.assertTrue(final[1]["wrap"])
        self.assertEqual(self.ctx.history().as_messages()[-1]["content"], "Hi https://a.fr")
        messages = self.client.chat_stream.call_args.args[0]
        self.assertEqual(messages[0], {"role": "system", "content": "Be brief."})

    def test_duplicate_ask_is_pending_until_the_first_finishes(self):
        self.client.chat_stream.return_value = iter([StreamChunk("a", False)])
        stream = commands.activate(self.ctx, "ask", {"query": "q"})
        next(stream)
        self.assertEqual(_actions(commands.activate(self.ctx, "ask", {"query": "q"})), [None])
        list(stream)
        self.client.chat_stream.return_value = iter([])
        self.assertIsNotNone(next(commands.activate(self.ctx, "ask", {"query": "q"})))

    def test_stream_error_offers_retry(self):
        self.client.chat_stream.side_effect = ApiTimeoutError()
        [error] = list(commands.activate(self.ctx, "ask", {"query": "q"}))
        self.assertEqual(_actions(error), [None, "ask"])
        self.assertEqual(error[1]["payload"], {"query": "q"})

    def test_empty_stream_is_an_error(self):
        self.client.chat_stream.return_value = iter([StreamChunk("", False)])
        [error] = list(commands.activate(self.ctx, "ask", {"query": "q"}))
        self.assertEqual(error[0]["description"], self.ctx.t("error.api_response"))

    def test_copy_closes_the_window(self):
        effect = commands.activate(self.ctx, "copy", {"text": "answer"})
        self.assertEqual(self.copied, ["answer"])
        self.assertEqual(effect["type"], "effect:close_window")

    def test_set_model_overrides_the_preference(self):
        commands.activate(self.ctx, "model:set", {"model": "large"})
        self.assertEqual(self.ctx.model, "large")

    def test_handler_failure_becomes_an_error_item_with_retry(self):
        self.client.list_models.side_effect = RuntimeError("boom")
        with self.assertLogs(commands.logger, "ERROR"):
            items = commands.activate(self.ctx, "model", {})
        self.assertEqual(_actions(items), [None, "model"])

    def test_unknown_action_shows_help(self):
        self.assertEqual(_actions(commands.activate(self.ctx, "nope", {})), [None])

    def test_last_shows_the_stored_answer(self):
        self.assertEqual(_actions(commands.suggest(self.ctx, "last")), [None])
        self.client.chat_stream.return_value = iter([StreamChunk("a", False)])
        list(commands.activate(self.ctx, "ask", {"query": "q"}))
        self.assertEqual(commands.suggest(self.ctx, "last")[0]["payload"], {"text": "a"})
