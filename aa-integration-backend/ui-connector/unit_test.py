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
"""Unit tests for the UI Connector SocketIO events and REST APIs."""

# pylint: disable=wrong-import-position,protected-access,broad-exception-caught
# pylint: disable=unspecified-encoding,line-too-long,missing-function-docstring,missing-class-docstring

import gzip
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("GCP_PROJECT_ID", "fake_project_id")
os.environ.setdefault("LOGGING_FILE", "/tmp/test.log")
os.environ.setdefault("JWT_SECRET_KEY_PATH", "/tmp/jwt_secret_key")
try:
    with open("/tmp/jwt_secret_key", "w", encoding="utf-8") as _f:
        _f.write("fake_jwt_secret_key")
except Exception:
    pass

# Mock redis library before importing main to prevent actual connections during unit tests
mock_redis = MagicMock()
mock_pubsub = MagicMock()
mock_redis.StrictRedis.return_value.pubsub.return_value = mock_pubsub
sys.modules["redis"] = mock_redis

import google.auth

google.auth.default = MagicMock(return_value=(MagicMock(), "fake_project_id"))

import dialogflow
import main
from main import app, redis_pubsub_handler, socketio
import webchannel  # pylint: disable=unused-import

_SERVER_ID = "fake_server_id"
_PROJECT_ID = "fake_project_id"
_LOCATION = "global"


def get_conversation_profile_name(conversation_profile_id):
    return ("projects/"
            f"{_PROJECT_ID}/locations/{_LOCATION}/"
            f"conversationProfiles/{conversation_profile_id}")


def get_conversation_name(conversation_id):
    return ("projects/"
            f"{_PROJECT_ID}/locations/{_LOCATION}/"
            f"conversations/{conversation_id}")


def get_conversation_name_without_location(conversation_id):
    return f"projects/{_PROJECT_ID}/conversations/{conversation_id}"


class FakeRawHTTPResponse:

    def __init__(self, data):
        self.data = data


class TestSocketIO(unittest.TestCase):
    """Unit tests for APIs related to SocketIO events."""

    def setUp(self):
        self.valid_jwt = main.generate_jwt()
        self.server_id = _SERVER_ID

    def tearDown(self):
        pass

    @patch("main.redis_client.delete")
    def test_connect(self, unused_mock_delete):
        """Establishes websocket connection with valid JWT."""
        client1 = socketio.test_client(app, auth={"token": self.valid_jwt})
        client2 = socketio.test_client(app, auth={"token": self.valid_jwt})
        self.assertTrue(client1.is_connected())
        self.assertTrue(client2.is_connected())
        self.assertNotEqual(client1.eio_sid, client2.eio_sid)
        client1.disconnect()
        self.assertFalse(client1.is_connected())
        self.assertTrue(client2.is_connected())
        client2.disconnect()
        self.assertFalse(client2.is_connected())

    def test_connect_failure(self):
        """Tries to establish websocket connection without valid JWT."""
        client = socketio.test_client(app, auth={"token": "invalid_jwt"})
        self.assertFalse(client.is_connected())

    def test_disconnect(self):
        """Disconnects websocket connection."""
        client = socketio.test_client(app, auth={"token": self.valid_jwt})
        client.disconnect()
        self.assertFalse(client.is_connected())

    @patch("main.redis_client.set")
    @patch("main.redis_client.delete")
    def test_join_conversation(self, mock_delete, mock_set):
        """Joins socketio room specified by conversation name."""
        conversation1 = get_conversation_name("conversation_001")
        conversation2 = get_conversation_name("conversation_002")
        conversation1_without_location = (
            get_conversation_name_without_location("conversation_001"))
        conversation2_without_location = (
            get_conversation_name_without_location("conversation_002"))
        # Sets client1 and client2 to join different rooms
        client1 = socketio.test_client(app, auth={"token": self.valid_jwt})
        client2 = socketio.test_client(app, auth={"token": self.valid_jwt})
        client1.get_received()
        client2.get_received()
        ack1, data1 = client1.emit("join-conversation",
                                   conversation1,
                                   callback=True)
        self.assertTrue(ack1)
        self.assertEqual(data1, conversation1_without_location)
        self.assertEqual(mock_set.call_count, 1)
        ack2, data2 = client2.emit("join-conversation",
                                   conversation2,
                                   callback=True)
        self.assertTrue(ack2)
        self.assertEqual(data2, conversation2_without_location)
        self.assertEqual(mock_set.call_count, 2)
        # Sends data to one room
        data = {"data": "fake_data"}
        socketio.emit(
            "conversation-lifecycle-event",
            data,
            to=conversation1_without_location,
        )
        received = client1.get_received()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["name"],
                         "conversation-lifecycle-event")  # event name
        self.assertEqual(received[0]["args"], [data])
        received = client2.get_received()
        self.assertEqual(len(received), 0)
        client1.disconnect()
        mock_delete.assert_called_with(conversation1_without_location)
        client2.disconnect()
        mock_delete.assert_called_with(conversation2_without_location)

    def test_redis_pubsub_handler(self):
        """Handles Redis Pub/Sub messages."""
        conversation1 = get_conversation_name("conversation_001")
        conversation2 = get_conversation_name("conversation_002")
        conversation1_without_location = (
            get_conversation_name_without_location("conversation_001"))

        dialogflow_event_sample1 = {
            "conversation": conversation1,
            "type": "CONVERSATION_STARTED",
        }
        redis_pubsub_pub_sample1 = {
            "conversation_name": conversation1_without_location,
            "data": json.dumps(dialogflow_event_sample1),
            "data_type": "conversation-lifecycle-event",
            "publish_time": "2021-12-09T20:05:37.275Z",
            "message_id": "3502221325816966",
        }
        redis_pubsub_sub_sample1 = {
            "type":
                "pmessage",
            "pattern":
                bytes(f"{self.server_id}*", encoding="raw_unicode_escape"),
            "channel":
                bytes(
                    f"{self.server_id}:{conversation1_without_location}",
                    encoding="raw_unicode_escape",
                ),
            "data":
                bytes(
                    json.dumps(redis_pubsub_pub_sample1),
                    encoding="raw_unicode_escape",
                ),
        }

        # Sets client1 and client2 to join different rooms
        client1 = socketio.test_client(app, auth={"token": self.valid_jwt})
        client2 = socketio.test_client(app, auth={"token": self.valid_jwt})
        client1.get_received()
        client2.get_received()
        client1.emit("join-conversation", conversation1)
        client2.emit("join-conversation", conversation2)
        client1.get_received()
        client2.get_received()
        # Publish to redis pubsub chanel for conversation1
        redis_pubsub_handler(redis_pubsub_sub_sample1)
        received = client1.get_received()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["name"], "conversation-lifecycle-event")
        self.assertEqual(received[0]["args"][0], redis_pubsub_pub_sample1)
        received = client2.get_received()
        self.assertEqual(len(received), 0)


class TestRestAPI(unittest.TestCase):
    """Unit tests for REST APIs."""

    @staticmethod
    def get_gzip_data(dict_data):
        return gzip.compress(json.dumps(dict_data).encode("utf-8"))

    @staticmethod
    def get_json_object(gzip_data):
        return json.loads(gzip.decompress(gzip_data).decode("utf-8"))

    class FakeGetConversationResponse:
        """Fake dialogflow response for GET conversations."""

        def __init__(self, conversation_profile_name, conversation_name,
                     header):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data({
                    "name": conversation_name,
                    "lifecycleState": "COMPLETED",
                    "conversationProfile": conversation_profile_name,
                    "startTime": "2021-11-09T21:50:16.522090Z",
                    "endTime": "2021-11-10T21:51:02.317614Z",
                    "conversationStage": "HUMAN_ASSIST_STAGE",
                }))
            self.status_code = 200
            self.headers = header

    class FakeCreateConversationResponse:
        """Fake dialogflow response for POST conversations."""

        def __init__(self, conversation_profile_name, conversation_name,
                     header):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data({
                    "name": conversation_name,
                    "lifecycleState": "IN_PROGRESS",
                    "conversationProfile": conversation_profile_name,
                    "startTime": "2021-12-09T20:05:36.638749Z",
                    "conversationStage": "HUMAN_ASSIST_STAGE",
                }))
            self.status_code = 200
            self.headers = header

    class FakeListAnswerRecordResponse:
        """Fake dialogflow response for GET answerRecords."""

        def __init__(self, answer_record, header):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data({
                    "answerRecords": [
                        answer_record,
                        {
                            "name": ("projects/"
                                     f"{_PROJECT_ID}/locations/{_LOCATION}/"
                                     "answerRecords/fake_answerrecord_002")
                        },
                    ],
                    "nextPageToken": "fake_next_page_token",
                }))
            self.status_code = 200
            self.headers = header

    class FakeUpdateAnswerRecordResponse:
        """Fake dialogflow response for PATCH answerRecords."""

        def __init__(self, answer_record):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data(answer_record))
            self.status_code = 200
            self.headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "Vary": "Origin, X-Origin, Referer",
                "Content-Encoding": "gzip",
                "Date": "Fri, 10 Dec 2021 18:40:17 GMT",
                "Server": "ESF",
                "Cache-Control": "private",
                "X-XSS-Protection": "0",
                "X-Frame-Options": "SAMEORIGIN",
                "X-Content-Type-Options": "nosniff",
                "Alt-Svc":
                    ('h3=":443"; ma=2592000,h3-29=":443"; ma=2592000,'
                     'h3-Q050=":443"; ma=2592000,h3-Q046=":443"; ma=2592000,'
                     'h3-Q043=":443"; ma=2592000,quic=":443"; ma=2592000; '
                     'v="46,43"'),
                "Transfer-Encoding": "chunked",
            }

    class FakeCompleteConversationResponse:
        """Fake dialogflow response for POST complete conversation."""

        def __init__(self, conversation_profile_name, conversation_name,
                     header):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data({
                    "name": conversation_name,
                    "lifecycleState": "COMPLETED",
                    "conversationProfile": conversation_profile_name,
                    "startTime": "2021-12-10T20:46:29.127983Z",
                    "endTime": "2021-12-10T20:46:29.715573Z",
                    "conversationStage": "HUMAN_ASSIST_STAGE",
                }))
            self.status_code = 200
            self.headers = header

    def setUp(self):
        self.valid_jwt = main.generate_jwt()
        self.answer_record = {
            "name": ("projects/"
                     f"{_PROJECT_ID}/locations/{_LOCATION}/"
                     "answerRecords/fake_answerrecord_001"),
            "answerFeedback": {
                "correctnessLevel": "PARTIALLY_CORRECT",
                "clicked": True,
                "displayed": True,
                "clickTime": "2021-12-09T20:13:36.638749Z",
                "displayTime": "2021-12-09T20:07:36.638749Z",
            },
        }
        self.header = {
            "Content-Type": "application/json; charset=UTF-8",
            "Vary": "Origin, X-Origin, Referer",
            "Content-Encoding": "gzip",
            "Date": "Thu, 09 Dec 2021 20:05:37 GMT",
            "Server": "ESF",
            "Cache-Control": "private",
            "X-XSS-Protection": "0",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "Transfer-Encoding": "chunked",
        }
        self.conversation_profile_id = "fake_conversation_profile_id"
        self.conversation_id = "fake_conversation_id"
        self.conversation_profile_name = get_conversation_profile_name(
            self.conversation_profile_id)
        self.conversation_name = get_conversation_name(self.conversation_id)

    def tearDown(self):
        pass

    def test_register_jwt_auth_unset(self):
        client = app.test_client()
        response = client.post("/register",
                               headers={"Authorization": "fake-auth"})
        self.assertEqual(
            response.status_code,
            401,
            "Please customize authentication rules before deploying your"
            " service.",
        )

    def test_dialogflow_get_conversation(self):
        """Gets information about a conversation with valid JWT."""
        client = app.test_client()
        get_conversation_response = self.FakeGetConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch(
                "dialogflow.get_dialogflow",
                return_value=(get_conversation_response),
        ):
            response = client.get(
                "/v2beta1/projects/"
                f"{_PROJECT_ID}/locations/{_LOCATION}/"
                f"conversations/{self.conversation_id}",
                headers={"Authorization": self.valid_jwt},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "application/json; charset=UTF-8")
        json_data = self.get_json_object(response.data)
        self.assertEqual(self.conversation_name, json_data["name"])

    def test_dialogflow_get_failure(self):
        """Tries to get information about a conversation without valid JWT."""
        client = app.test_client()
        get_conversation_response = self.FakeGetConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch(
                "dialogflow.get_dialogflow",
                return_value=(get_conversation_response),
        ):
            response = client.get("/v2beta1/projects/"
                                  f"{_PROJECT_ID}/locations/{_LOCATION}/"
                                  f"conversations/{self.conversation_id}")
        self.assertEqual(response.get_json(), {"message": "Token is missing."})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_dialogflow_create_conversation(self):
        """Creates a conversation with valid JWT."""
        client = app.test_client()
        create_conversation_response = self.FakeCreateConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch(
                "dialogflow.post_dialogflow",
                return_value=(create_conversation_response),
        ):
            response = client.post(
                "/v2beta1/projects/"
                f"{_PROJECT_ID}/locations/{_LOCATION}/conversations",
                json={"conversation_profile": self.conversation_profile_name},
                headers={"Authorization": self.valid_jwt},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "application/json; charset=UTF-8")
        json_data = self.get_json_object(response.data)
        self.assertIn("name", json_data)
        self.assertEqual(json_data["lifecycleState"], "IN_PROGRESS")
        self.assertEqual(json_data["conversationProfile"],
                         self.conversation_profile_name)
        self.assertIn("startTime", json_data)
        self.assertIn("conversationStage", json_data)

    def test_dialogflow_update_answerrecord(self):
        """Updates an answer record with valid JWT."""
        client = app.test_client()
        update_answer_record_response = self.FakeUpdateAnswerRecordResponse(
            self.answer_record)
        with patch(
                "dialogflow.patch_dialogflow",
                return_value=(update_answer_record_response),
        ):
            response = client.patch(
                "/v2beta1/projects/"
                f"{_PROJECT_ID}/locations/{_LOCATION}/answerRecords/"
                "fake_answerrecord_001?updateMask=answerFeedback",
                json=self.answer_record,
                headers={"Authorization": self.valid_jwt},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "application/json; charset=UTF-8")
        self.assertEqual(self.get_json_object(response.data),
                         self.answer_record)

    def test_dialogflow_complete_conversation(self):
        """Completes a conversation with valid JWT."""
        client = app.test_client()
        complete_conversation_response = self.FakeCompleteConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch(
                "dialogflow.post_dialogflow",
                return_value=(complete_conversation_response),
        ):
            response = client.post(
                "/v2beta1/projects/"
                f"{_PROJECT_ID}/locations/{_LOCATION}/"
                f"conversations/{self.conversation_id}:complete",
                headers={"Authorization": self.valid_jwt},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "application/json; charset=UTF-8")
        json_data = self.get_json_object(response.data)
        self.assertEqual(json_data["name"], self.conversation_name)
        self.assertEqual(json_data["lifecycleState"], "COMPLETED")
        self.assertEqual(json_data["conversationProfile"],
                         self.conversation_profile_name)
        self.assertIn("startTime", json_data)
        self.assertIn("endTime", json_data)
        self.assertIn("conversationStage", json_data)

    def test_dialogflow_unavailable(self):
        """Tries to send unavailable Dialogflow requests."""
        client = app.test_client()
        response = client.delete(
            f"/v2beta1/projects/{_PROJECT_ID}/locations/{_LOCATION}/invalidPath"
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Not Found", response.data)
        self.assertEqual(response.headers["Content-Type"],
                         "text/html; charset=utf-8")


class TestDialogflowModule(unittest.TestCase):
    """Unit tests for dialogflow.py helper functions and session handling."""

    def test_get_authed_session_raises_when_none(self):
        with patch.object(dialogflow, "AUTHED_SESSION", None):
            with self.assertRaises(RuntimeError) as ctx:
                dialogflow._get_authed_session()
            self.assertIn("No credentials available", str(ctx.exception))

    def test_get_authed_session_returns_session(self):
        mock_session = MagicMock()
        with patch.object(dialogflow, "AUTHED_SESSION", mock_session):
            self.assertEqual(dialogflow._get_authed_session(), mock_session)


class TestHttpStreamingCompanion(unittest.TestCase):
    """Unit tests for SocketIO streaming RPC proxy handlers in main.py."""

    def test_location_regex(self):
        res = (
            "projects/p1/locations/us-central1/conversations/c1/participants/p1"
        )
        match = main.LOCATION_REGEX.search(res)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "us-central1")

        res_global = "projects/p1/conversations/c1/participants/p1"
        match_global = main.LOCATION_REGEX.search(res_global)
        self.assertIsNone(match_global)

    @patch("main.socketio.emit")
    def test_handle_stream_request_missing_method(self, mock_emit):
        with app.test_request_context():
            main.request.sid = "test-sid"
            main.handle_stream_request({"streamId": "s-missing", "payload": {}})
            mock_emit.assert_called_with(
                "stream-error",
                {
                    "streamId": "s-missing",
                    "payload": {
                        "error": {
                            "message": ('Missing required "method" parameter in'
                                        " initial stream-request."),
                            "code": 13,
                        }
                    },
                },
                to="test-sid",
            )

    @patch("main.socketio.emit")
    def test_handle_stream_request_unknown_method(self, mock_emit):
        with app.test_request_context():
            main.request.sid = "test-sid"
            main.handle_stream_request({
                "streamId": "s-unknown",
                "method": "invalid_method"
            })
            mock_emit.assert_called_with(
                "stream-error",
                {
                    "streamId": "s-unknown",
                    "payload": {
                        "error": {
                            "message":
                                ("Unknown streaming method: invalid_method"),
                            "code": 13,
                        }
                    },
                },
                to="test-sid",
            )

    @patch("main.socketio.emit")
    def test_handle_stream_request_missing_location(self, mock_emit):
        with app.test_request_context():
            main.request.sid = "test-sid"
            main.handle_stream_request({
                "streamId": "s-no-loc",
                "method": "streaming_reactive_companion_suggestions",
                "payload": {
                    "participant": "invalid/resource/path"
                },
            })
            mock_emit.assert_called_with(
                "stream-error",
                {
                    "streamId": "s-no-loc",
                    "payload": {
                        "error": {
                            "message":
                                ("Could not extract location from participant: "
                                 '"invalid/resource/path".'),
                            "code": 13,
                        }
                    },
                },
                to="test-sid",
            )

    @patch("webchannel.WebChannelClient")
    def test_handle_stream_request_new_stream_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        with app.test_request_context():
            main.request.sid = "test-sid-1"
            main.handle_stream_request({
                "streamId": "s-success",
                "method": "streaming_reactive_companion_suggestions",
                "payload": {
                    "participant":
                        ("projects/p1/locations/us-central1/conversations/c1/"
                         "participants/p1")
                },
            })
            mock_client.connect.assert_called_once()
            mock_client.send.assert_called_once()
            self.assertIn("s-success", main.ACTIVE_STREAMS)
            self.assertIn("s-success",
                          main.SOCKET_SESSION_IDS_TO_STREAMS["test-sid-1"])

    @patch("webchannel.WebChannelClient")
    def test_handle_stream_request_already_active_forwards_payload(
            self, mock_client_cls):
        mock_client = MagicMock()
        main.ACTIVE_STREAMS["s-active"] = mock_client
        with app.test_request_context():
            main.request.sid = "test-sid-1"
            main.handle_stream_request({
                "streamId": "s-active",
                "payload": {
                    "text": "hello"
                },
            })
            mock_client_cls.assert_not_called()
            mock_client.send.assert_called_once_with({"text": "hello"})

    def test_handle_end_stream_cleans_resources(self):
        mock_client = MagicMock()
        main.ACTIVE_STREAMS["test-s1"] = mock_client
        main.SOCKET_SESSION_IDS_TO_STREAMS.setdefault("test-sid",
                                                      set()).add("test-s1")

        with app.test_request_context():
            main.request.sid = "test-sid"
            main.handle_end_stream({"streamId": "test-s1"})

        mock_client.close.assert_called_once()
        self.assertNotIn("test-s1", main.ACTIVE_STREAMS)
        self.assertNotIn(
            "test-s1",
            main.SOCKET_SESSION_IDS_TO_STREAMS.get("test-sid", set()))

    def test_stream_on_close_cleans_resources(self):
        main.ACTIVE_STREAMS["test-s2"] = MagicMock()
        main.SOCKET_SESSION_IDS_TO_STREAMS.setdefault("test-sid-2",
                                                      set()).add("test-s2")
        main._cleanup_stream("test-sid-2", "test-s2")
        self.assertNotIn("test-s2", main.ACTIVE_STREAMS)
        self.assertNotIn(
            "test-s2",
            main.SOCKET_SESSION_IDS_TO_STREAMS.get("test-sid-2", set()),
        )


if __name__ == "__main__":
    unittest.main()
