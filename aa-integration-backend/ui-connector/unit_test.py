# Copyright 2022 Google LLC
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

import unittest
import json
import gzip
from unittest.mock import patch, call

import main
from main import socketio
from main import app
from main import dialogflow
from main import redis_pubsub_handler

_SERVER_ID = 'fake_server_id'
_PROJECT_ID = 'fake_project_id'
_LOCATION = 'global'


def get_conversation_profile_name(conversation_profile_id):
    return 'projects/{0}/locations/{1}/conversationProfiles/{2}'.format(
        _PROJECT_ID, _LOCATION, conversation_profile_id)


def get_conversation_name(conversation_id):
    return 'projects/{0}/locations/{1}/conversations/{2}'.format(
        _PROJECT_ID, _LOCATION, conversation_id)


def get_conversation_name_without_location(conversation_id):
    return 'projects/{0}/conversations/{1}'.format(
        _PROJECT_ID, conversation_id)


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

    @patch('main.redis_client.delete')
    def test_connect(self, MockDelete):
        """Establishes websocket connection with valid JWT."""
        client1 = socketio.test_client(app, auth={'token': self.valid_jwt})
        client2 = socketio.test_client(app, auth={'token': self.valid_jwt})
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
        client = socketio.test_client(app, auth={'token': 'invalid_jwt'})
        received = client.get_received()
        self.assertRaises(ConnectionRefusedError)
        # TODO check whether the behaviour is secure enough
        self.assertTrue(client.is_connected())
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['name'], 'unauthenticated')  # event name
        self.assertEqual(received[0]['args'], [])

    def test_disconnect(self):
        """Disconnects websocket connection."""
        client = socketio.test_client(app, auth={'token': self.valid_jwt})
        client.disconnect()
        self.assertFalse(client.is_connected())

    @patch('main.redis_client.set')
    @patch('main.redis_client.delete')
    def test_join_conversation(self, MockDelete, MockSet):
        """Joins socketio room specified by conversation name."""
        conversation1 = get_conversation_name('conversation_001')
        conversation2 = get_conversation_name('conversation_002')
        # Sets client1 and client2 to join different rooms
        client1 = socketio.test_client(app, auth={'token': self.valid_jwt})
        client2 = socketio.test_client(app, auth={'token': self.valid_jwt})
        client1.get_received()
        client2.get_received()
        ack1, data1 = client1.emit(
            'join-conversation', conversation1, callback=True)
        self.assertTrue(ack1)
        self.assertEqual(data1, conversation1)
        self.assertEqual(MockSet.call_count, 2)
        ack2, data2 = client2.emit(
            'join-conversation', conversation2, callback=True)
        self.assertTrue(ack2)
        self.assertEqual(data2, conversation2)
        self.assertEqual(MockSet.call_count, 4)
        # Sends data to one room
        data = {'data': 'fake_data'}
        socketio.emit('conversation-lifecycle-event', data, to=conversation1)
        received = client1.get_received()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['name'],
                         'conversation-lifecycle-event')  # event name
        self.assertEqual(received[0]['args'], [data])
        received = client2.get_received()
        self.assertEqual(len(received), 0)
        client1.disconnect()
        MockDelete.assert_has_calls(
            [call(conversation1, get_conversation_name_without_location('conversation_001'))])
        client2.disconnect()
        MockDelete.assert_has_calls(
            [call(conversation2, get_conversation_name_without_location('conversation_002'))])

    def test_redis_pubsub_handler(self):
        """Handles Redis Pub/Sub messages."""
        conversation1 = get_conversation_name('conversation_001')
        conversation2 = get_conversation_name('conversation_002')

        dialogflow_event_sample1 = {
            'conversation': conversation1,
            'type': 'CONVERSATION_STARTED'
        }
        redis_pubsub_pub_sample1 = {
            'conversation_name': conversation1,
            'data': json.dumps(dialogflow_event_sample1),
            'data_type': 'conversation-lifecycle-event',
            'publish_time': '2021-12-09T20:05:37.275Z',
            'message_id': '3502221325816966'
        }
        redis_pubsub_sub_sample1 = {
            'type': 'pmessage',
            'pattern': bytes('{}*'.format(self.server_id), encoding='raw_unicode_escape'),
            'channel': bytes('{0}:{1}'.format(self.server_id, conversation1), encoding='raw_unicode_escape'),
            'data': bytes(json.dumps(redis_pubsub_pub_sample1), encoding='raw_unicode_escape')
        }

        # Sets client1 and client2 to join different rooms
        client1 = socketio.test_client(app, auth={'token': self.valid_jwt})
        client2 = socketio.test_client(app, auth={'token': self.valid_jwt})
        client1.get_received()
        client2.get_received()
        client1.emit('join-conversation', conversation1)
        client2.emit('join-conversation', conversation2)
        client1.get_received()
        client2.get_received()
        # Publish to redis pubsub chanel for conversation1
        redis_pubsub_handler(redis_pubsub_sub_sample1)
        received = client1.get_received()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['name'], 'conversation-lifecycle-event')
        self.assertEqual(received[0]['args'][0], redis_pubsub_pub_sample1)
        received = client2.get_received()
        self.assertEqual(len(received), 0)


class TestRestAPI(unittest.TestCase):
    """Unit tests for REST APIs."""

    @staticmethod
    def get_gzip_data(dict_data):
        return gzip.compress(json.dumps(dict_data).encode('utf-8'))

    @staticmethod
    def get_json_object(gzip_data):
        return json.loads(gzip.decompress(gzip_data).decode('utf-8'))

    class FakeGetConversationResponse:
        """Fake dialogflow response for
            GET '/v2beta1/projects/<project_id>/locations/<location>/conversations/<conversation_id>'.
        """

        def __init__(self, conversation_profile_name, conversation_name, header):
            self.raw = FakeRawHTTPResponse(TestRestAPI.get_gzip_data({
                'name': conversation_name,
                'lifecycleState': 'COMPLETED',
                'conversationProfile': conversation_profile_name,
                'startTime': '2021-11-09T21:50:16.522090Z',
                'endTime': '2021-11-10T21:51:02.317614Z',
                'conversationStage': 'HUMAN_ASSIST_STAGE'
            }))
            self.status_code = 200
            self.headers = header

    class FakeCreateConversationResponse:
        """Fake dialogflow response for
            POST '/v2beta1/projects/<project_id>/locations/<location>/conversations'.
        """

        def __init__(self, conversation_profile_name, conversation_name, header):
            self.raw = FakeRawHTTPResponse(TestRestAPI.get_gzip_data({
                'name': conversation_name,
                'lifecycleState': 'IN_PROGRESS',
                'conversationProfile': conversation_profile_name,
                'startTime': '2021-12-09T20:05:36.638749Z',
                'conversationStage': 'HUMAN_ASSIST_STAGE'
            }))
            self.status_code = 200
            self.headers = header

    class FakeListAnswerRecordResponse:
        """Fake dialogflow response for
            GET '/locations/<location>/answerRecords'.
        """

        def __init__(self, answer_record, header):
            self.raw = FakeRawHTTPResponse(TestRestAPI.get_gzip_data({
                'answerRecords':
                [
                    answer_record,
                    {
                        'name': 'projects/{0}/locations/{1}/answerRecords/fake_answerrecord_002'.format(
                            _PROJECT_ID, _LOCATION)
                    }
                ],
                'nextPageToken': 'fake_next_page_token'
            }))
            self.status_code = 200
            self.headers = header

    class FakeUpdateAnswerRecordResponse:
        """Fake dialogflow response for
            PATCH '/v2beta1/projects/<project_id>/locations/<location>/answerRecords/<answerrecord_id>?updateMask=answerFeedback'.
        """

        def __init__(self, answer_record):
            self.raw = FakeRawHTTPResponse(
                TestRestAPI.get_gzip_data(answer_record))
            self.status_code = 200
            self.headers = {
                'Content-Type': 'application/json; charset=UTF-8',
                'Vary': 'Origin, X-Origin, Referer',
                'Content-Encoding': 'gzip',
                'Date': 'Fri, 10 Dec 2021 18:40:17 GMT',
                'Server': 'ESF',
                'Cache-Control': 'private',
                'X-XSS-Protection': '0',
                'X-Frame-Options': 'SAMEORIGIN',
                'X-Content-Type-Options': 'nosniff',
                'Alt-Svc': 'h3=":443"; ma=2592000,h3-29=":443"; ma=2592000,h3-Q050=":443"; ma=2592000,h3-Q046=":443"; ma=2592000,h3-Q043=":443"; ma=2592000,quic=":443"; ma=2592000; v="46,43"',
                'Transfer-Encoding': 'chunked'
            }

    class FakeCompleteConversationResponse:
        """Fake dialogflow response for
            POST '/v2beta1/projects/<project_id>/locations/<location>/conversations/<conversation_id>:complete'.
        """

        def __init__(self, conversation_profile_name, conversation_name, header):
            self.raw = FakeRawHTTPResponse(TestRestAPI.get_gzip_data({
                'name': conversation_name,
                'lifecycleState': 'COMPLETED',
                'conversationProfile': conversation_profile_name,
                'startTime': '2021-12-10T20:46:29.127983Z',
                'endTime': '2021-12-10T20:46:29.715573Z',
                'conversationStage': 'HUMAN_ASSIST_STAGE'
            }))
            self.status_code = 200
            self.headers = header

    def setUp(self):
        self.valid_jwt = main.generate_jwt()
        self.answer_record = {
            'name': 'projects/{0}/locations/{1}/answerRecords/fake_answerrecord_001'.format(
                _PROJECT_ID, _LOCATION),
            'answerFeedback': {
                'correctnessLevel': 'PARTIALLY_CORRECT',
                'clicked': True,
                'displayed': True,
                'clickTime': '2021-12-09T20:13:36.638749Z',
                'displayTime': '2021-12-09T20:07:36.638749Z'
            }
        }
        self.header = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Vary': 'Origin, X-Origin, Referer',
            'Content-Encoding': 'gzip',
            'Date': 'Thu, 09 Dec 2021 20:05:37 GMT',
            'Server': 'ESF',
            'Cache-Control': 'private',
            'X-XSS-Protection': '0',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Transfer-Encoding': 'chunked'
        }
        self.conversation_profile_id = 'fake_conversation_profile_id'
        self.conversation_id = 'fake_conversation_id'
        self.conversation_profile_name = get_conversation_profile_name(
            self.conversation_profile_id)
        self.conversation_name = get_conversation_name(self.conversation_id)

    def tearDown(self):
        pass

    def test_register_JWT_auth_unset(self):
        client = app.test_client()
        response = client.post(
            '/register', headers={'Authorization': 'fake-auth'})
        self.assertEqual(response.status_code, 401,
                         'Please customize authentication rules before deploying your service.')

    def test_dialogflow_get_conversation(self):
        """Gets information about a conversation with valid JWT."""
        client = app.test_client()
        get_conversation_response = self.FakeGetConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch('dialogflow.get_dialogflow', return_value=(get_conversation_response)):
            response = client.get(
                '/v2beta1/projects/{0}/locations/{1}/conversations/{2}'.format(
                    _PROJECT_ID, _LOCATION, self.conversation_id),
                headers={'Authorization': self.valid_jwt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'application/json; charset=UTF-8')
        json_data = self.get_json_object(response.data)
        self.assertEqual(self.conversation_name, json_data['name'])

    def test_dialogflow_get_failure(self):
        """Tries to get information about a conversation without valid JWT."""
        client = app.test_client()
        get_conversation_response = self.FakeGetConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch('dialogflow.get_dialogflow', return_value=(get_conversation_response)):
            response = client.get(
                '/v2beta1/projects/{0}/locations/{1}/conversations/{2}'.format(_PROJECT_ID, _LOCATION, self.conversation_id))
        self.assertEqual(response.get_json(), {'message': 'Token is missing.'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

    def test_dialogflow_create_conversation(self):
        """Creates a conversation with valid JWT."""
        client = app.test_client()
        create_conversation_response = self.FakeCreateConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch('dialogflow.post_dialogflow', return_value=(create_conversation_response)):
            response = client.post(
                '/v2beta1/projects/{0}/locations/{1}/conversations'.format(
                    _PROJECT_ID, _LOCATION),
                json={'conversation_profile': self.conversation_profile_name},
                headers={'Authorization': self.valid_jwt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'application/json; charset=UTF-8')
        json_data = self.get_json_object(response.data)
        self.assertIn('name', json_data)
        self.assertEqual(json_data['lifecycleState'], 'IN_PROGRESS')
        self.assertEqual(
            json_data['conversationProfile'], self.conversation_profile_name)
        self.assertIn('startTime', json_data)
        self.assertIn('conversationStage', json_data)

    def test_dialogflow_list_answerrecord(self):
        """Lists answer records with valid JWT."""
        client = app.test_client()
        list_answer_record_response = self.FakeListAnswerRecordResponse(
            self.answer_record, self.header)
        with patch('dialogflow.get_dialogflow', return_value=(list_answer_record_response)):
            response = client.get(
                '/v2beta1/projects/{0}/locations/{1}/answerRecords?pageSize=2'.format(
                    _PROJECT_ID, _LOCATION),
                headers={'Authorization': self.valid_jwt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'application/json; charset=UTF-8')
        json_data = self.get_json_object(response.data)
        self.assertEqual(len(json_data['answerRecords']), 2)

    def test_dialogflow_update_answerrecord(self):
        """Updates an answer record with valid JWT."""
        client = app.test_client()
        update_answer_record_response = self.FakeUpdateAnswerRecordResponse(
            self.answer_record)
        with patch('dialogflow.patch_dialogflow', return_value=(update_answer_record_response)):
            response = client.patch(
                '/v2beta1/projects/{0}/locations/{1}/answerRecords/fake_answerrecord_001?updateMask=answerFeedback'.format(
                    _PROJECT_ID, _LOCATION),
                json=self.answer_record,
                headers={'Authorization': self.valid_jwt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(self.get_json_object(
            response.data), self.answer_record)

    def test_dialogflow_complete_conversation(self):
        """Completes a conversation with valid JWT."""
        client = app.test_client()
        complete_conversation_response = self.FakeCompleteConversationResponse(
            self.conversation_profile_name, self.conversation_name, self.header)
        with patch('dialogflow.post_dialogflow', return_value=(complete_conversation_response)):
            response = client.post(
                '/v2beta1/projects/{0}/locations/{1}/conversations/{2}:complete'.format(
                    _PROJECT_ID, _LOCATION, self.conversation_id),
                headers={'Authorization': self.valid_jwt})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'application/json; charset=UTF-8')
        json_data = self.get_json_object(response.data)
        self.assertEqual(json_data['name'], self.conversation_name)
        self.assertEqual(json_data['lifecycleState'], 'COMPLETED')
        self.assertEqual(
            json_data['conversationProfile'], self.conversation_profile_name)
        self.assertIn('startTime', json_data)
        self.assertIn('endTime', json_data)
        self.assertIn('conversationStage', json_data)

    def test_dialogflow_unavailable(self):
        """Tries to send unavailable Dialogflow requests."""
        client = app.test_client()
        response = client.delete(
            '/v2beta1/projects/{0}/locations/{1}/conversationProfiles/{2}'.format(
                _PROJECT_ID, _LOCATION, self.conversation_profile_id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n')
        self.assertEqual(
            response.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(response.headers['Content-Length'], '232')


if __name__ == '__main__':
    unittest.main()
