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

import time
import unittest
from unittest.mock import MagicMock, patch

import webchannel


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

    def test_create_webchannel_get_url(self):
        url = webchannel.create_webchannel_get_url(
            "https://example.com/channel", "sid-abc", "gsess-xyz")
        self.assertEqual(
            url,
            "https://example.com/channel?VER=8&RID=rpc&SID=sid-abc&"
            "gsessionid=gsess-xyz&AID=0&CI=0&TYPE=xmlhttp",
        )

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

    def test_decode_webchannel_payload(self):
        chunk = '[[1, [{"response_chunk": "hi", "is_final": false}]]]'
        events = webchannel._decode_webchannel_payload(chunk)
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0],
            {
                "type": "data",
                "payload": {
                    "responseChunk": "hi",
                    "isFinal": False
                },
            },
        )

        error_chunk = '[[1, [{"error": {"message": "session expired"}}]]]'
        events = webchannel._decode_webchannel_payload(error_chunk)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], {
            "type": "error",
            "payload": "session expired"
        })

        list_error_chunk = (
            '[[1, [[{"error": {"code": 400, "message": "bad request"}}]]]]')
        events = webchannel._decode_webchannel_payload(list_error_chunk)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], {"type": "error", "payload": "bad request"})

        invalid_chunks = ["", "not a json"]
        for invalid in invalid_chunks:
            events = webchannel._decode_webchannel_payload(invalid)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["type"], "error")
            self.assertIn("Error parsing response", events[0]["payload"])


class TestWebChannelClient(unittest.TestCase):
    """Unit tests for WebChannelClient streaming and error handling."""

    @patch("webchannel.CREDENTIALS", None)
    def test_connect_without_credentials_emits_error(self):
        client = webchannel.WebChannelClient("https://example.com/channel",
                                             credentials=None)
        received_errors = []
        client.onError(lambda e: received_errors.append(e))
        client.connect()
        self.assertIn("No credentials available for AuthorizedSession.",
                      received_errors)

    @patch("webchannel.AuthorizedSession")
    def test_normal_streaming_lifecycle(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        init_response = MagicMock()
        init_response.status_code = 200
        init_response.text = '[[0,["c","sid-123","",8,14]]]'
        init_response.headers = {"x-http-session-id": "gsess-1"}
        mock_session.post.return_value = init_response

        payload = '[[1, [{"response_chunk": "hello", "is_final": true}]]]'
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.iter_content.return_value = [f"{len(payload)}\n{payload}"]
        mock_session.get.return_value = get_response

        mock_creds = MagicMock()
        mock_creds.token = "fake_token"

        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=mock_creds)
        received_data = []
        client.onResponse(lambda p: received_data.append(p))

        client.connect()
        client.send({"textInput": "hello"})

        time.sleep(0.1)

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], {
            "responseChunk": "hello",
            "isFinal": True
        })
        client.close(reason="test_cleanup")

    @patch("webchannel.AuthorizedSession")
    def test_init_non_200_emits_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        init_response = MagicMock()
        init_response.status_code = 403
        init_response.text = "Forbidden"
        mock_session.post.return_value = init_response

        mock_creds = MagicMock()
        mock_creds.token = "fake_token"

        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=mock_creds)
        received_errors = []
        client.onError(lambda e: received_errors.append(e))

        client.connect()
        client.send({"textInput": "hello"})

        time.sleep(0.1)

        self.assertTrue(any("403" in str(e) for e in received_errors))
        client.close(reason="test_cleanup")

    @patch("webchannel.AuthorizedSession")
    def test_get_stream_non_200_emits_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        init_response = MagicMock()
        init_response.status_code = 200
        init_response.text = '[[0,["c","sid-123","",8,14]]]'
        init_response.headers = {"x-http-session-id": "gsess-1"}
        mock_session.post.return_value = init_response

        get_response = MagicMock()
        get_response.status_code = 502
        get_response.text = "Bad Gateway"
        mock_session.get.return_value = get_response

        mock_creds = MagicMock()
        mock_creds.token = "fake_token"

        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=mock_creds)
        received_errors = []
        client.onError(lambda e: received_errors.append(e))

        client.connect()
        client.send({"textInput": "hello"})

        time.sleep(0.1)

        self.assertTrue(any("502" in str(e) for e in received_errors))
        client.close(reason="test_cleanup")

    @patch("webchannel.AuthorizedSession")
    def test_post_request_non_200_emits_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        init_response = MagicMock()
        init_response.status_code = 200
        init_response.text = '[[0,["c","sid-123","",8,14]]]'
        init_response.headers = {"x-http-session-id": "gsess-1"}

        post_response = MagicMock()
        post_response.status_code = 500
        post_response.text = "Internal Server Error"

        mock_session.post.side_effect = [init_response, post_response]

        get_response = MagicMock()
        get_response.status_code = 200
        get_response.iter_content.return_value = []
        mock_session.get.return_value = get_response

        mock_creds = MagicMock()
        mock_creds.token = "fake_token"

        client = webchannel.WebChannelClient("https://test-url/channel",
                                             credentials=mock_creds)
        received_errors = []
        client.onError(lambda e: received_errors.append(e))

        client.connect()
        client.send({"textInput": "hello"})

        time.sleep(0.1)

        self.assertTrue(any("500" in str(e) for e in received_errors))
        client.close(reason="test_cleanup")

    def test_multiple_posts_increment_ofs(self):
        mock_session = MagicMock()
        post_response = MagicMock()
        post_response.status_code = 200
        post_response.text = "8\n[0,0,7]"
        mock_session.post.return_value = post_response

        client = webchannel.WebChannelClient("https://test-url/channel")
        client.rid = 10
        client.message_offset = 0

        client._do_post_requests(
            session=mock_session,
            requests_to_send=[{
                "textInput": "first"
            }],
            post_headers={},
            webchannel_sid="sid-123",
            gsessionid="gsess-1",
        )
        client._do_post_requests(
            session=mock_session,
            requests_to_send=[{
                "textInput": "second"
            }],
            post_headers={},
            webchannel_sid="sid-123",
            gsessionid="gsess-1",
        )

        self.assertEqual(mock_session.post.call_count, 2)
        first_call_data = mock_session.post.call_args_list[0][1]["data"]
        second_call_data = mock_session.post.call_args_list[1][1]["data"]
        self.assertIn("ofs=0", first_call_data)
        self.assertIn("ofs=1", second_call_data)
        self.assertEqual(client.rid, 12)
        self.assertEqual(client.message_offset, 2)

    def test_on_close_callback(self):
        client = webchannel.WebChannelClient("https://test-url/channel")
        closed = []
        client.onClose(lambda: closed.append(True))
        client.close(reason="test_termination")
        self.assertTrue(client.stopped)
        self.assertEqual(closed, [True])
        sentinel = client.active_stream_queue.get_nowait()
        self.assertEqual(sentinel, "STOP")

    def test_do_post_requests_bundles_payloads(self):
        client = webchannel.WebChannelClient("https://test-url/channel")
        client.rid = 100
        client.message_offset = 5
        mock_session = MagicMock()
        post_resp = MagicMock()
        post_resp.status_code = 200
        mock_session.post.return_value = post_resp

        client._do_post_requests(
            session=mock_session,
            requests_to_send=[{
                "text": "a"
            }, {
                "text": "b"
            }],
            post_headers={"Content-Type": "application/json"},
            webchannel_sid="sid-1",
            gsessionid="gsess-1",
        )

        self.assertEqual(mock_session.post.call_count, 1)
        call_args, call_kwargs = mock_session.post.call_args
        self.assertIn("RID=100", call_args[0])
        self.assertIn("count=2", call_kwargs["data"])
        self.assertIn("ofs=5", call_kwargs["data"])
        self.assertIn("req0___data__=%7B%22text%22%3A%20%22a%22%7D",
                      call_kwargs["data"])
        self.assertIn("req1___data__=%7B%22text%22%3A%20%22b%22%7D",
                      call_kwargs["data"])
        self.assertEqual(client.rid, 101)
        self.assertEqual(client.message_offset, 7)


if __name__ == "__main__":
    unittest.main()
