import io
import unittest
import urllib.error
from unittest import mock

from mistral.client import MistralClient, StreamChunk
from mistral.errors import ApiError, ApiKeyMissingError, ApiResponseError, NetworkError


class _Response(io.BytesIO):
    pass


def _sse(*lines):
    return _Response("".join(f"{line}\n\n" for line in lines).encode())


class MistralClientTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("urllib.request.urlopen")
        self.urlopen = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = MistralClient("key")

    def _stream(self):
        return list(self.client.chat_stream([], model="m", max_tokens=10))

    def test_requires_api_key(self):
        with self.assertRaises(ApiKeyMissingError):
            MistralClient("")

    def test_stream_yields_deltas_and_truncation(self):
        self.urlopen.return_value = _sse(
            'data: {"choices":[{"delta":{"content":"Hel"}}]}',
            ": keep-alive",
            'data: {"choices":[{"delta":{"content":"lo"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
            "data: [DONE]",
        )
        self.assertEqual(
            self._stream(),
            [
                StreamChunk("Hel", truncated=False),
                StreamChunk("lo", truncated=False),
                StreamChunk("", truncated=True),
            ],
        )
        request = self.urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer key")

    def test_malformed_chunk_becomes_response_error(self):
        self.urlopen.return_value = _sse("data: {oops")
        with self.assertRaises(ApiResponseError):
            self._stream()

    def test_http_error_keeps_status(self):
        self.urlopen.side_effect = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, io.BytesIO(b"bad key")
        )
        with self.assertRaises(ApiError) as caught:
            self._stream()
        self.assertEqual(caught.exception.status, 401)
        self.assertEqual(caught.exception.message_key, "error.api_401")

    def test_network_error(self):
        self.urlopen.side_effect = urllib.error.URLError("unreachable")
        with self.assertRaises(NetworkError):
            self.client.list_models()

    def test_list_models_sorted_unique(self):
        self.urlopen.return_value = _Response(b'{"data":[{"id":"b"},{"id":"a"},{"id":"b"}]}')
        self.assertEqual(self.client.list_models(), ["a", "b"])
