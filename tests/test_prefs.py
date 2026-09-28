import unittest

from prefs import Preferences, load_specs


class PreferencesTest(unittest.TestCase):
    specs = load_specs()

    def test_defaults_come_from_manifest(self):
        prefs = Preferences({}, self.specs)
        self.assertEqual(prefs.text("default_model"), "mistral-small-latest")
        self.assertEqual(prefs.number("history_size"), 4)

    def test_numbers_are_clamped_to_manifest_bounds(self):
        prefs = Preferences({"history_size": 99, "max_tokens": 10**6, "timeout": 1}, self.specs)
        self.assertEqual(prefs.number("history_size"), 20)
        self.assertEqual(prefs.number("max_tokens"), 32768)
        self.assertEqual(prefs.number("timeout"), 5)

    def test_corrupt_number_falls_back_to_default(self):
        self.assertEqual(Preferences({"timeout": ""}, self.specs).number("timeout"), 30)

    def test_text_is_stripped(self):
        self.assertEqual(Preferences({"api_key": " k \n"}, self.specs).text("api_key"), "k")
