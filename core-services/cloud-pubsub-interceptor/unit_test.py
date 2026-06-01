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
import base64
from unittest.mock import Mock, patch
import datetime

import main
from main import app

SERVER_ID = 'SERVER_001'
CONVERSATION_ID = 'fake-conversation-001'
PROJECT_ID = 'aa-integration-poc'
CONVERSATION_NAME = 'projects/{0}/locations/global/conversations/{1}'.format(
    PROJECT_ID, CONVERSATION_ID)
SAMPLE_DIALOGFLOW_EVENT = {
    'conversation': CONVERSATION_NAME,
    'type': 'CONVERSATION_STARTED'
}
SAMPLE_REDIS_PUBSUB_PUB = {
    'conversation_name': CONVERSATION_NAME,
    'data': json.dumps(SAMPLE_DIALOGFLOW_EVENT),
    'data_type': 'conversation-lifecycle-event',
    'ack_time': '2022-03-11T00:00:10Z',
    'publish_time': '2022-03-11T00:00:00Z',
    'message_id': '3502221325816966'
}
SAMPLE_CLOUD_PUBSUB_MSG = {
    'message': {
        'data': base64.b64encode(json.dumps(SAMPLE_DIALOGFLOW_EVENT).encode('utf-8')).decode('ascii'),
        'publishTime': '2022-03-11T00:00:00Z',
        'messageId': '3502221325816966'
    }
}


class TestInterceptorAPI(unittest.TestCase):
    """Unit tests for Cloud Pub/Sub Interceptor APIs."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch('main.datetime')
    @patch('main.redis_client.exists', return_value=1)
    @patch('main.redis_client.get', return_value=bytes(SERVER_ID, encoding='raw_unicode_escape'))
    @patch('main.redis_client.publish')
    def test_cloud_pubsub_handler(self, MockPublish, MockGet, MockExists, MockDateTime):
        """Handles messages posted by Cloud Pub/Sub."""
        MockDateTime.now = Mock(
            return_value=datetime.datetime(2022, 3, 11, 0, 0, 10))
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_CLOUD_PUBSUB_MSG)
        MockPublish.assert_called_with(
            '{}:{}'.format(SERVER_ID, CONVERSATION_NAME),
            json.dumps(SAMPLE_REDIS_PUBSUB_PUB))
        MockGet.assert_called_with(CONVERSATION_NAME)
        MockExists.assert_called_with(CONVERSATION_NAME)
        self.assertEqual(MockDateTime.now.call_count, 1)
        self.assertEqual(response.status_code, 204)

    @patch('main.datetime')
    @patch('main.redis_client.exists', return_value=1)
    @patch('main.redis_client.get', return_value=bytes(SERVER_ID, encoding='raw_unicode_escape'))
    @patch('main.redis_client.publish')
    def test_missing_json_failure(self, MockPublish, MockGet, MockExists, MockDateTime):
        """Rejects HTTP requests without a request body."""
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event')
        self.assertFalse(MockPublish.called)
        self.assertFalse(MockGet.called)
        self.assertFalse(MockExists.called)
        self.assertFalse(MockDateTime.called)
        # Ack messeages to avoid unnecessary retry.
        self.assertEqual(response.status_code, 204)

    @patch('main.datetime')
    @patch('main.redis_client.exists', return_value=1)
    @patch('main.redis_client.get', return_value=bytes(SERVER_ID, encoding='raw_unicode_escape'))
    @patch('main.redis_client.publish')
    def test_wrong_message_format_failure(self, MockPublish, MockGet, MockExists, MockDateTime):
        """Rejects HTTP requests with wrong body format."""
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_DIALOGFLOW_EVENT)
        self.assertFalse(MockPublish.called)
        self.assertFalse(MockGet.called)
        self.assertFalse(MockExists.called)
        self.assertFalse(MockDateTime.called)
        # Ack messeages to avoid unnecessary retry.
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
