# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for webchannel.py HTTP streaming client and protocol helpers."""

# pylint: disable=protected-access,unnecessary-lambda,missing-function-docstring,missing-class-docstring

import asyncio
import json
import re
import threading
import time
import unittest
from unittest import mock

import aiohttp
from google.auth import exceptions as google_auth_exceptions

import webchannel

INIT_TEXT = '[[0,["c","sid-123","",8,14]]]'
DATA_FRAME = [1, [{"response_chunk": "hello", "is_final": True}]]
DATA_PAYLOAD = {"responseChunk": "hello", "isFinal": True}
WAVE = "\U0001F44B"  # 1 Python character, 2 UTF-16 code units.


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _chunk(*frames) -> str:
    """Length-prefixes `[aid, body]` frames the way the server does."""
    payload = json.dumps(list(frames), ensure_ascii=False)
    return f"{_utf16_len(payload)}\n{payload}"


def _mock_credentials(token="fake_token"):
    creds = mock.MagicMock()
    creds.token = token
    creds.expired = False
    return creds


class FakeResponse:
    """aiohttp response double usable with `async with`."""

    def __init__(self,
                 status=200,
                 text="",
                 headers=None,
                 chunks=(),
                 hang=False,
                 raise_after=None):
        self.status = status
        self.headers = headers or {}
        self.content = self
        self._text = text
        self._chunks = chunks
        self._hang = hang
        self._raise_after = raise_after

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def text(self):
        return self._text

    async def iter_any(self):
        for chunk in self._chunks:
            yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
        if self._raise_after is not None:
            raise self._raise_after
        if self._hang:
            await asyncio.sleep(3600)


class FakeSession:
    """aiohttp.ClientSession double replaying scripted POST/GET responses."""

    def __init__(self, post_responses, get_responses=()):
        self.post_responses = list(post_responses)
        self.get_responses = list(get_responses)
        self.post_calls = []
        self.get_urls = []
        self.get_started = threading.Event()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def post(self, url, data=None, **unused_kwargs):
        self.post_calls.append((url, data))
        return self._next(self.post_responses)

    def get(self, url, **unused_kwargs):
        self.get_urls.append(url)
        self.get_started.set()
        return self._next(self.get_responses)

    @staticmethod
    def _next(responses):
        """Pops the next scripted response, repeating the last one."""
        response = responses.pop(0) if len(responses) > 1 else responses[0]
        if isinstance(response, Exception):
            raise response
        return response


def _init_response():
    return FakeResponse(text=INIT_TEXT,
                        headers={"x-http-session-id": "gsess-1"})


def _post_response(status=200, text="8\n[1,0,7]"):
    return FakeResponse(status=status, text=text)


def _close_response(*frames):
    return FakeResponse(chunks=[_chunk(*frames), _chunk([99, ["close"]])])


class TestWebChannelUrlHelpers(unittest.TestCase):
    """Unit tests for WebChannel URL and header construction functions."""

    def test_get_webchannel_post_headers(self):
        headers = webchannel.get_webchannel_post_headers("test_token")
        self.assertEqual(headers["Authorization"], "Bearer test_token")
        self.assertEqual(headers["X-WebChannel-Content-Type"],
                         "application/json")
        self.assertEqual(headers["Content-Type"],
                         "application/x-www-form-urlencoded")
        self.assertEqual(headers["X-Goog-Api-Client"], "gl-python")

    def test_get_webchannel_get_headers(self):
        headers = webchannel.get_webchannel_get_headers("test_token")
        self.assertEqual(headers["Authorization"], "Bearer test_token")
        self.assertEqual(headers["X-Goog-Api-Client"], "gl-python")

    def test_create_webchannel_init_url(self):
        url = webchannel.create_webchannel_init_url(
            "https://example.com/channel", 12345)
        self.assertEqual(
            url,
            "https://example.com/channel?VER=8&MODE=init&RID=12345&"
            "X-HTTP-Session-Id=gsessionid",
        )

    def test_create_webchannel_post_url(self):
        url = webchannel.create_webchannel_post_url(
            "https://example.com/channel", 100, "sid-abc", "gsess-xyz")
        self.assertEqual(
            url,
            "https://example.com/channel?VER=8&RID=100&SID=sid-abc&"
            "gsessionid=gsess-xyz&AID=0",
        )
        url = webchannel.create_webchannel_post_url(
            "https://example.com/channel", 100, "sid-abc", "gsess-xyz", aid=7)
        self.assertTrue(url.endswith("&AID=7"))

    def test_create_webchannel_get_url(self):
        url = webchannel.create_webchannel_get_url(
            "https://example.com/channel", "sid-abc", "gsess-xyz")
        self.assertEqual(
            url,
            "https://example.com/channel?VER=8&RID=rpc&SID=sid-abc&"
            "gsessionid=gsess-xyz&AID=0&CI=0&TYPE=xmlhttp",
        )
        url = webchannel.create_webchannel_get_url(
            "https://example.com/channel", "sid-abc", "gsess-xyz", aid=7)
        self.assertIn("&AID=7&CI=0&", url)

    def test_extract_webchannel_sid(self):
        resp_text = '[[0,["c","test-sid-999","",8,14]]]'
        self.assertEqual(webchannel.extract_webchannel_sid(resp_text),
                         "test-sid-999")

        invalid_text = '[[0,["noop"]]]'
        self.assertIsNone(webchannel.extract_webchannel_sid(invalid_text))

    def test_get_streaming_rpc_url(self):
        channel_path = ("google.cloud.dialogflow.v2beta1.Participants/"
                        "StreamingReactiveCompanionSuggestions/channel")
        self.assertEqual(
            webchannel.get_streaming_rpc_url(channel_path, "global"),
            "https://global-dialogflow-webchannel.googleapis.com/" +
            channel_path,
        )
        self.assertEqual(
            webchannel.get_streaming_rpc_url(channel_path, "us-central1"),
            "https://us-central1-dialogflow-webchannel.googleapis.com/" +
            channel_path,
        )

    def test_get_streaming_rpc_url_rejects_host_injection(self):
        for location in ("evil.example#", "evil.example/", "a@b", "", "US"):
            with self.assertRaises(ValueError, msg=location):
                webchannel.get_streaming_rpc_url("channel", location)

    def test_format_webchannel_message(self):
        formatted = webchannel._format_webchannel_message({"query": "test"},
                                                          count=2,
                                                          ofs=5)
        self.assertIn("count=2", formatted)
        self.assertIn("ofs=5", formatted)
        self.assertIn("req0___data__=%7B%22query%22%3A%20%22test%22%7D",
                      formatted)

    def test_format_webchannel_message_multiple(self):
        formatted = webchannel._format_webchannel_message([{
            "a": 1
        }, {
            "b": 2
        }],
                                                          ofs=3)
        self.assertIn("count=2", formatted)
        self.assertIn("ofs=3", formatted)
        self.assertIn("req0___data__=%7B%22a%22%3A%201%7D", formatted)
        self.assertIn("req1___data__=%7B%22b%22%3A%202%7D", formatted)


class TestWebChannelDataTransforms(unittest.TestCase):
    """Unit tests for WebChannel framing, decoding, and JSON normalizing."""

    def test_snake_to_camel(self):
        snake_dict = {
            "response_chunk": "hello",
            "token_consumption": 10,
            "nested_item": {
                "is_final": True
            },
            "list_items": [{
                "inner_key": 1
            }],
        }
        camel = webchannel.snake_to_camel(snake_dict)
        self.assertEqual(
            camel,
            {
                "responseChunk": "hello",
                "tokenConsumption": 10,
                "nestedItem": {
                    "isFinal": True
                },
                "listItems": [{
                    "innerKey": 1
                }],
            },
        )

    def test_extract_webchannel_chunks(self):
        buffer = "10\n12345678905\nabcde1\n1"
        chunks, remaining = webchannel._extract_webchannel_chunks(buffer)
        self.assertEqual(chunks, ["1234567890", "abcde", "1"])
        self.assertEqual(remaining, "")

        buffer = "\n\n10\n1234567890\n"
        chunks, remaining = webchannel._extract_webchannel_chunks(buffer)
        self.assertEqual(chunks, ["1234567890"])
        self.assertEqual(remaining, "")

        buffer = "10\n12345"
        chunks, remaining = webchannel._extract_webchannel_chunks(buffer)
        self.assertEqual(chunks, [])
        self.assertEqual(remaining, "10\n12345")

    def test_extract_webchannel_chunks_counts_utf16_code_units(self):
        wave_frame = f'[[1,["{WAVE}"]]]'  # 11 characters, 12 code units.
        buffer = f'12\n{wave_frame}12\n[[2,["ok"]]]'
        chunks, remaining = webchannel._extract_webchannel_chunks(buffer)
        self.assertEqual(chunks, [wave_frame, '[[2,["ok"]]]'])
        self.assertEqual(remaining, "")

        partial = f"12\n{wave_frame[:-1]}"
        chunks, remaining = webchannel._extract_webchannel_chunks(partial)
        self.assertEqual(chunks, [])
        self.assertEqual(remaining, partial)

    def test_extract_webchannel_chunks_rejects_oversized_prefix(self):
        with self.assertRaises(ValueError):
            webchannel._extract_webchannel_chunks(
                f"{webchannel.MAX_CHUNK_UTF16_UNITS + 1}\n[")

    def test_decode_webchannel_payload(self):
        chunk = '[[1, [{"response_chunk": "hi", "is_final": false}]]]'
        self.assertEqual(
            webchannel._decode_webchannel_payload(chunk),
            [{
                "type": "data",
                "aid": 1,
                "payload": {
                    "responseChunk": "hi",
                    "isFinal": False
                },
            }],
        )

        error_chunk = '[[1, [{"error": {"message": "session expired"}}]]]'
        self.assertEqual(webchannel._decode_webchannel_payload(error_chunk), [{
            "type": "error",
            "aid": 1,
            "payload": "session expired"
        }])

        list_error_chunk = (
            '[[1, [[{"error": {"code": 400, "message": "bad request"}}]]]]')
        self.assertEqual(
            webchannel._decode_webchannel_payload(list_error_chunk), [{
                "type": "error",
                "aid": 1,
                "payload": "bad request"
            }])

        invalid_chunks = ["", "not a json"]
        for invalid in invalid_chunks:
            events = webchannel._decode_webchannel_payload(invalid)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["type"], "error")
            self.assertIn("Error parsing response", events[0]["payload"])

    def test_decode_webchannel_payload_control_frames(self):
        chunk = ('[[1, ["noop"]], [2, ["stop"]], [3, ["close"]], '
                 '[4, {"__sm__": {"status": {}}}]]')
        events = webchannel._decode_webchannel_payload(chunk)
        self.assertEqual([e["type"] for e in events],
                         ["noop", "close", "close", "metadata"])
        self.assertEqual([e["aid"] for e in events], [1, 2, 3, 4])
        self.assertEqual(events[1]["payload"], "stop")
        self.assertEqual(events[2]["payload"], "close")


class TestWebChannelClient(unittest.TestCase):
    """Unit tests for WebChannelClient streaming and error handling."""

    def _new_client(self):
        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=_mock_credentials())
        events = {"data": [], "errors": [], "closed": []}
        client.onResponse(lambda p: events["data"].append(p))
        client.onError(lambda e: events["errors"].append(e))
        client.onClose(lambda: events["closed"].append(True))
        return client, events

    def _run_stream(self, session):
        """Streams one payload through `session` until the stream ends."""
        client, events = self._new_client()
        with mock.patch("webchannel.aiohttp.ClientSession",
                        return_value=session):
            client.connect()
            client.send({"textInput": "hello"})
            client._stream_future.result(timeout=5)
        return client, events

    @mock.patch("webchannel.CREDENTIALS", None)
    def test_connect_without_credentials_emits_error(self):
        client = webchannel.WebChannelClient("https://example.com/channel",
                                             credentials=None)
        received_errors = []
        client.onError(lambda e: received_errors.append(e))
        client.connect()
        self.assertIn("No credentials available for WebChannel stream.",
                      received_errors)
        self.assertTrue(client.stopped)

    def test_normal_streaming_lifecycle(self):
        session = FakeSession(
            [_init_response(), _post_response()], [_close_response(DATA_FRAME)])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(events["errors"], [])
        self.assertEqual(events["closed"], [True])
        self.assertTrue(client.stopped)
        init_url, init_data = session.post_calls[0]
        self.assertIn("MODE=init", init_url)
        self.assertEqual(init_data, "count=0")
        post_url, post_data = session.post_calls[1]
        init_rid = int(re.search(r"RID=(\d+)", init_url).group(1))
        self.assertIn(f"RID={init_rid + 1}&", post_url)
        self.assertIn("SID=sid-123&gsessionid=gsess-1&AID=0", post_url)
        self.assertIn("count=1&ofs=0&req0___data__=", post_data)
        self.assertEqual(session.get_urls, [
            "https://test-url/channel?VER=8&RID=rpc&SID=sid-123&"
            "gsessionid=gsess-1&AID=0&CI=0&TYPE=xmlhttp"
        ])

    def test_noop_frames_are_filtered_and_aid_tracked(self):
        get_response = FakeResponse(chunks=[
            _chunk([1, ["noop"]]),
            _chunk([2, DATA_FRAME[1]], [3, ["noop"]]),
            _chunk([4, ["close"]]),
        ])
        session = FakeSession(
            [_init_response(), _post_response()], [get_response])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(client.last_aid, 4)
        self.assertTrue(client.stopped)

    def test_backchannel_get_reconnects_after_eof(self):
        second_frame = [2, [{"response_chunk": "again", "is_final": False}]]
        session = FakeSession(
            [_init_response(), _post_response()], [
                FakeResponse(chunks=[_chunk(DATA_FRAME)]),
                _close_response(second_frame),
            ])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [
            DATA_PAYLOAD,
            {
                "responseChunk": "again",
                "isFinal": False
            },
        ])
        self.assertEqual(events["errors"], [])
        self.assertEqual(len(session.get_urls), 2)
        self.assertIn("&AID=0&", session.get_urls[0])
        self.assertIn("&AID=1&", session.get_urls[1])
        self.assertTrue(client.stopped)

    def test_multibyte_frames_split_across_reads(self):
        wave_frame = [1, [{"response_chunk": f"hi {WAVE}", "is_final": False}]]
        wire = (_chunk(wave_frame) +
                _chunk([2, DATA_FRAME[1]], [3, ["close"]])).encode("utf-8")
        # Split inside the 4-byte emoji so one read ends mid-character.
        split = wire.index(WAVE.encode("utf-8")) + 2
        get_response = FakeResponse(chunks=[wire[:split], wire[split:]])
        session = FakeSession(
            [_init_response(), _post_response()], [get_response])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [
            {
                "responseChunk": f"hi {WAVE}",
                "isFinal": False
            },
            DATA_PAYLOAD,
        ])
        self.assertEqual(events["errors"], [])
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_backchannel_get_retries_transient_failure(self):
        session = FakeSession(
            [_init_response(), _post_response()], [
                aiohttp.ClientConnectionError("connection reset"),
                _close_response(DATA_FRAME),
            ])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(events["errors"], [])
        self.assertEqual(len(session.get_urls), 2)
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_backchannel_get_gives_up_after_max_retries(self):
        session = FakeSession(
            [_init_response(), _post_response()],
            [aiohttp.ClientConnectionError("reset")])

        client, events = self._run_stream(session)

        self.assertEqual(len(session.get_urls),
                         webchannel.BACKCHANNEL_MAX_RETRIES + 1)
        self.assertTrue(
            any("after 3 retries" in str(e) for e in events["errors"]))
        self.assertEqual(events["closed"], [True])
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_idle_timeouts_after_frames_reconnect_without_limit(self):
        # Each GET delivers a heartbeat, then idles out: the server's normal
        # rotation during a quiet call, repeated past the retry budget.
        idle_gets = [
            FakeResponse(chunks=[_chunk([aid, ["noop"]])],
                         raise_after=aiohttp.SocketTimeoutError("idle"))
            for aid in range(1, webchannel.BACKCHANNEL_MAX_RETRIES + 3)
        ]
        session = FakeSession(
            [_init_response(), _post_response()],
            idle_gets + [_close_response([50, DATA_FRAME[1]])])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(events["errors"], [])
        self.assertEqual(len(session.get_urls), len(idle_gets) + 1)
        self.assertIn(f"&AID={len(idle_gets)}&", session.get_urls[-1])
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_empty_gets_without_frames_exhaust_retry_budget(self):
        # An endpoint answering every GET with an immediate empty 200 must not
        # turn into a tight reconnect loop on the shared event loop.
        session = FakeSession(
            [_init_response(), _post_response()], [FakeResponse(chunks=[])])

        client, events = self._run_stream(session)

        self.assertEqual(len(session.get_urls),
                         webchannel.BACKCHANNEL_MAX_RETRIES + 1)
        self.assertTrue(
            any("after 3 retries" in str(e) for e in events["errors"]))
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_backchannel_retries_5xx_and_refresh_transport_errors(self):
        session = FakeSession(
            [_init_response(), _post_response()], [
                FakeResponse(status=503, text="unavailable"),
                google_auth_exceptions.TransportError("metadata server"),
                _close_response(DATA_FRAME),
            ])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(events["errors"], [])
        self.assertEqual(len(session.get_urls), 3)
        self.assertTrue(client.stopped)

    def test_backchannel_4xx_closes_stream(self):
        session = FakeSession(
            [_init_response(), _post_response()],
            [FakeResponse(status=400, text="Unknown SID")])

        client, events = self._run_stream(session)

        self.assertTrue(any("400" in str(e) for e in events["errors"]))
        self.assertEqual(len(session.get_urls), 1)
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_backchannel_frames_reset_retry_budget(self):
        error = aiohttp.ClientConnectionError("reset")
        session = FakeSession(
            [_init_response(), _post_response()], [
                error,
                error,
                error,
                FakeResponse(chunks=[_chunk([1, ["noop"]])]),
                error,
                error,
                error,
                _close_response([2, DATA_FRAME[1]]),
            ])

        client, events = self._run_stream(session)

        self.assertEqual(events["data"], [DATA_PAYLOAD])
        self.assertEqual(events["errors"], [])
        self.assertEqual(len(session.get_urls), 8)
        self.assertTrue(client.stopped)

    @mock.patch("webchannel.FIRST_MESSAGE_TIMEOUT", 0.01)
    def test_connect_without_send_times_out(self):
        session = FakeSession([_init_response()])
        client, events = self._new_client()

        with mock.patch("webchannel.aiohttp.ClientSession",
                        return_value=session):
            client.connect()
            client._stream_future.result(timeout=5)

        self.assertTrue(client.stopped)
        self.assertEqual(events["closed"], [True])
        self.assertEqual(events["errors"], [])
        self.assertEqual(session.post_calls, [])

    def test_close_cancels_hanging_backchannel(self):
        session = FakeSession(
            [_init_response(), _post_response()], [FakeResponse(hang=True)])
        client, events = self._new_client()

        with mock.patch("webchannel.aiohttp.ClientSession",
                        return_value=session):
            client.connect()
            client.send({"textInput": "hello"})
            self.assertTrue(session.get_started.wait(timeout=5))
            client.close(reason="test_cleanup")
            client._stream_future.result(timeout=5)

        self.assertTrue(client.stopped)
        self.assertEqual(events["closed"], [True])
        self.assertEqual(events["errors"], [])

    def test_init_non_200_emits_error(self):
        session = FakeSession([FakeResponse(status=403, text="Forbidden")])

        client, events = self._run_stream(session)

        self.assertTrue(any("403" in str(e) for e in events["errors"]))
        self.assertTrue(client.stopped)
        self.assertEqual(session.get_urls, [])

    @mock.patch("webchannel.BACKCHANNEL_RETRY_BASE_SECONDS", 0)
    def test_get_stream_persistent_5xx_emits_error(self):
        session = FakeSession(
            [_init_response(), _post_response()],
            [FakeResponse(status=502, text="Bad Gateway")])

        client, events = self._run_stream(session)

        self.assertEqual(len(session.get_urls),
                         webchannel.BACKCHANNEL_MAX_RETRIES + 1)
        self.assertTrue(any("HTTP 502" in str(e) for e in events["errors"]))
        self.assertTrue(client.stopped)

    def test_post_request_non_200_closes_stream(self):
        session = FakeSession(
            [_init_response(),
             _post_response(500, "Internal Server Error")], [_close_response()])

        client, events = self._run_stream(session)

        self.assertTrue(any("500" in str(e) for e in events["errors"]))
        self.assertEqual(events["closed"], [True])
        self.assertEqual(events["data"], [])
        self.assertTrue(client.stopped)

    def test_next_batch_drops_payloads_queued_with_close(self):
        client, _ = self._new_client()
        client._outbound.put_nowait({"textInput": "late"})
        client._outbound.put_nowait(webchannel.STOP_SIGNAL)
        self.assertEqual(asyncio.run(client._next_batch()), [])

    def test_post_failure_mid_stream_stops_backchannel(self):
        session = FakeSession([
            _init_response(),
            _post_response(),
            _post_response(404, "session gone")
        ], [FakeResponse(hang=True)])
        client, events = self._new_client()

        with mock.patch("webchannel.aiohttp.ClientSession",
                        return_value=session):
            client.connect()
            client.send({"textInput": "hello"})
            self.assertTrue(session.get_started.wait(timeout=5))
            client.send({"textInput": "again"})
            client._stream_future.result(timeout=5)

        self.assertTrue(any("404" in str(e) for e in events["errors"]))
        self.assertEqual(events["closed"], [True])
        self.assertTrue(client.stopped)

    def test_server_error_frame_closes_stream(self):
        session = FakeSession([
            _init_response(), _post_response()
        ], [
            FakeResponse(chunks=[_chunk([1, [{
                "error": {
                    "message": "boom"
                }
            }]])])
        ])

        client, events = self._run_stream(session)

        self.assertEqual(events["errors"], ["boom"])
        self.assertEqual(events["data"], [])
        self.assertTrue(client.stopped)

    def test_do_post_requests_bundles_payloads_and_increments_counters(self):
        client, _ = self._new_client()
        client.rid = 100
        client.message_offset = 5
        client.last_aid = 7
        session = FakeSession([_post_response()])

        asyncio.run(
            client._do_post_requests(session, [{
                "text": "a"
            }, {
                "text": "b"
            }], "sid-1", "gsess-1"))
        asyncio.run(
            client._do_post_requests(session, [{
                "text": "c"
            }], "sid-1", "gsess-1"))

        self.assertEqual(len(session.post_calls), 2)
        first_url, first_data = session.post_calls[0]
        self.assertIn("RID=100&SID=sid-1&gsessionid=gsess-1&AID=7", first_url)
        self.assertIn("count=2", first_data)
        self.assertIn("ofs=5", first_data)
        self.assertIn("req0___data__=%7B%22text%22%3A%20%22a%22%7D", first_data)
        self.assertIn("req1___data__=%7B%22text%22%3A%20%22b%22%7D", first_data)
        self.assertIn("ofs=7", session.post_calls[1][1])
        self.assertEqual(client.rid, 102)
        self.assertEqual(client.message_offset, 8)

    def test_ensure_valid_token_refreshes_expired_credentials(self):
        creds = _mock_credentials(token=None)
        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=creds)
        asyncio.run(client._ensure_valid_token())
        creds.refresh.assert_called_once()

        creds = _mock_credentials()
        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=creds)
        self.assertEqual(asyncio.run(client._ensure_valid_token()),
                         "fake_token")
        creds.refresh.assert_not_called()

    def test_concurrent_token_refreshes_collapse_into_one(self):
        creds = _mock_credentials(token=None)

        def slow_refresh(unused_request):
            time.sleep(0.05)  # Let every stream observe the expiry first.
            creds.token = "fresh_token"

        creds.refresh.side_effect = slow_refresh
        clients = [
            webchannel.WebChannelClient("https://test-url/channel",
                                        credentials=creds) for _ in range(5)
        ]

        async def refresh_all():
            return await asyncio.gather(
                *(client._ensure_valid_token() for client in clients))

        self.assertEqual(asyncio.run(refresh_all()), ["fresh_token"] * 5)
        creds.refresh.assert_called_once()

    def test_on_close_callback(self):
        client, events = self._new_client()
        client.close(reason="test_termination")
        client.close(reason="already_stopped")
        self.assertTrue(client.stopped)
        self.assertEqual(events["closed"], [True])


if __name__ == "__main__":
    unittest.main()
