import unittest

from mistral.formatter import extract_urls


class ExtractUrlsTest(unittest.TestCase):
    def test_trims_prose_punctuation_and_deduplicates(self):
        text = "See https://a.fr/x. Then (https://b.fr) and https://a.fr/x!"
        self.assertEqual(extract_urls(text), ["https://a.fr/x", "https://b.fr"])

    def test_keeps_balanced_brackets(self):
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        self.assertEqual(extract_urls(f"[{url}]"), [url])

    def test_drops_userinfo_urls(self):
        self.assertEqual(extract_urls("https://trusted.com@evil.tld/login"), [])
