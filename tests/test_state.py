import tempfile
import unittest
from pathlib import Path

from mistral.conversation import ConversationHistory
from mistral.state import StateStore


class StateTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "sub" / "state.json"
        self.store = StateStore(self.path)


class StateStoreTest(StateTestCase):
    def test_persists_across_instances(self):
        self.store.set("model", "mistral-large")
        self.assertEqual(StateStore(self.path).get("model"), "mistral-large")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_corrupt_file_reads_as_empty(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json")
        self.assertEqual(self.store.get("model", "default"), "default")

    def test_update_receives_current_value(self):
        self.store.set("n", 1)
        self.store.update("n", lambda n: n + 1)
        self.assertEqual(self.store.get("n"), 2)


class ConversationHistoryTest(StateTestCase):
    def test_keeps_last_exchanges_as_messages(self):
        history = ConversationHistory(self.store, max_exchanges=2)
        for i in range(3):
            history.add_exchange(f"q{i}", f"a{i}")
        self.assertEqual(
            history.as_messages(),
            [
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "q2"},
                {"role": "assistant", "content": "a2"},
            ],
        )
        history.clear()
        self.assertEqual(history.as_messages(), [])

    def test_disabled_history_stores_nothing(self):
        ConversationHistory(self.store, max_exchanges=0).add_exchange("q", "a")
        self.assertFalse(self.path.exists())
