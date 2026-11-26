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
from unittest.mock import Mock, patch, MagicMock
import datetime
import os
import sys

os.environ.setdefault('LOGGING_FILE', '/tmp/test.log')
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

if 'redis' not in sys.modules:
    try:
        import redis
    except ImportError:
        mock_redis = MagicMock()
        sys.modules['redis'] = mock_redis

import main
from main import app

SERVER_ID = 'SERVER_001'
CONVERSATION_ID = 'fake-conversation-001'
PROJECT_ID = 'aa-integration-poc'
CONVERSATION_NAME = 'projects/{0}/locations/global/conversations/{1}'.format(
    PROJECT_ID, CONVERSATION_ID)
CONVERSATION_NAME_WITHOUT_LOCATION = 'projects/{0}/conversations/{1}'.format(
    PROJECT_ID, CONVERSATION_ID)
SAMPLE_DIALOGFLOW_EVENT = {
    'conversation': CONVERSATION_NAME,
    'type': 'CONVERSATION_STARTED'
}
SAMPLE_REDIS_PUBSUB_PUB = {
    'conversation_name': CONVERSATION_NAME_WITHOUT_LOCATION,
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
    @patch('main.redis_client.smembers', return_value={bytes(SERVER_ID, encoding='raw_unicode_escape')})
    @patch('main.redis_client.publish')
    def test_cloud_pubsub_handler(self, MockPublish, MockSmembers, MockDateTime):
        """Handles messages posted by Cloud Pub/Sub."""
        MockDateTime.now = Mock(
            return_value=datetime.datetime(2022, 3, 11, 0, 0, 10))
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_CLOUD_PUBSUB_MSG)
        MockPublish.assert_called_once_with(
            '{}:{}'.format(SERVER_ID, CONVERSATION_NAME_WITHOUT_LOCATION),
            json.dumps(SAMPLE_REDIS_PUBSUB_PUB))
        MockSmembers.assert_called_once_with(
            main.get_conversation_servers_key(CONVERSATION_NAME_WITHOUT_LOCATION))
        self.assertEqual(MockDateTime.now.call_count, 1)
        self.assertEqual(response.status_code, 204)

    @patch('main.datetime')
    @patch('main.redis_client.smembers', return_value={b'SERVER_001', b'SERVER_002'})
    @patch('main.redis_client.publish')
    def test_cloud_pubsub_handler_fans_out_to_all_servers(self, MockPublish, unused_MockSmembers, MockDateTime):
        """Publishes to every UI Connector instance serving the conversation."""
        MockDateTime.now = Mock(
            return_value=datetime.datetime(2022, 3, 11, 0, 0, 10))
        conversation_name = main.get_conversation_name_without_location(
            CONVERSATION_NAME)
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_CLOUD_PUBSUB_MSG)
        self.assertCountEqual(
            [call.args[0] for call in MockPublish.call_args_list],
            ['SERVER_001:{}'.format(conversation_name),
             'SERVER_002:{}'.format(conversation_name)])
        self.assertEqual(response.status_code, 204)

    @patch('main.redis_client.smembers', return_value=set())
    @patch('main.redis_client.publish')
    def test_cloud_pubsub_handler_no_servers_acks_without_publish(self, MockPublish, unused_MockSmembers):
        """Acks without publishing when no instance serves the conversation."""
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_CLOUD_PUBSUB_MSG)
        self.assertFalse(MockPublish.called)
        self.assertEqual(response.status_code, 204)

    @patch('main.datetime')
    @patch('main.redis_client.smembers', return_value={bytes(SERVER_ID, encoding='raw_unicode_escape')})
    @patch('main.redis_client.publish')
    def test_missing_json_failure(self, MockPublish, MockSmembers, MockDateTime):
        """Rejects HTTP requests without a request body."""
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event')
        self.assertFalse(MockPublish.called)
        self.assertFalse(MockSmembers.called)
        self.assertFalse(MockDateTime.called)
        # Ack messeages to avoid unnecessary retry.
        self.assertEqual(response.status_code, 204)

    @patch('main.datetime')
    @patch('main.redis_client.smembers', return_value={bytes(SERVER_ID, encoding='raw_unicode_escape')})
    @patch('main.redis_client.publish')
    def test_wrong_message_format_failure(self, MockPublish, MockSmembers, MockDateTime):
        """Rejects HTTP requests with wrong body format."""
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event',
                               json=SAMPLE_DIALOGFLOW_EVENT)
        self.assertFalse(MockPublish.called)
        self.assertFalse(MockSmembers.called)
        self.assertFalse(MockDateTime.called)
        # Ack messeages to avoid unnecessary retry.
        self.assertEqual(response.status_code, 204)

    def test_get_redis_tls_kwargs_progressive_upgrade(self):
        """Verifies Redis TLS is opt-in and enforces TLS 1.2+ with CA verification."""
        import ssl
        import tempfile

        self.assertEqual(
            main.get_redis_tls_kwargs(False, '/secret/redis_ca_cert.pem', ''),
            {},
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem') as ca_file:
            ca_file.write('-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----\n')
            ca_file.flush()
            self.assertEqual(
                main.get_redis_tls_kwargs(True, ca_file.name, ''),
                {
                    'ssl': True,
                    'ssl_cert_reqs': 'required',
                    'ssl_min_version': ssl.TLSVersion.TLSv1_2,
                    'ssl_ca_certs': ca_file.name,
                },
            )

        self.assertEqual(
            main.get_redis_tls_kwargs(
                True,
                '/nonexistent/redis_ca_cert.pem',
                '-----BEGIN CERTIFICATE-----\\nFAKE\\n-----END CERTIFICATE-----',
            ),
            {
                'ssl': True,
                'ssl_cert_reqs': 'required',
                'ssl_min_version': ssl.TLSVersion.TLSv1_2,
                'ssl_ca_data': '-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----',
            },
        )

        with self.assertRaises(ValueError):
            main.get_redis_tls_kwargs(True, '/nonexistent/redis_ca_cert.pem', '')

    @patch('main.datetime')
    @patch('main.redis_client.smembers', return_value={bytes(SERVER_ID, encoding='raw_unicode_escape')})
    @patch('main.redis_client.publish')
    def test_invalid_pubsub_payload_acks_without_retry(
        self, MockPublish, MockSmembers, MockDateTime
    ):
        """Acks malformed base64, JSON, or non-dict payloads without crashing."""
        client = app.test_client()
        malformed_payloads = [
            {'message': {'data': '!!!not-base64!!!'}},
            {'message': {'data': base64.b64encode(b'{invalid-json').decode('ascii')}},
            {'message': {'data': base64.b64encode(b'["list-not-dict"]').decode('ascii')}},
        ]
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                response = client.post('/conversation-lifecycle-event',
                                       json=payload)
                self.assertEqual(response.status_code, 204)
        self.assertFalse(MockPublish.called)
        self.assertFalse(MockSmembers.called)
        self.assertFalse(MockDateTime.called)

    @patch('main.datetime')
    @patch('main.redis_client.smembers', return_value={bytes(SERVER_ID, encoding='raw_unicode_escape')})
    @patch('main.redis_client.publish')
    def test_missing_optional_pubsub_metadata_fields(
        self, MockPublish, unused_MockSmembers, MockDateTime
    ):
        """Handles Pub/Sub messages missing optional publishTime/messageId keys."""
        MockDateTime.now = Mock(
            return_value=datetime.datetime(2022, 3, 11, 0, 0, 10))
        payload = {
            'message': {
                'data': base64.b64encode(
                    json.dumps(SAMPLE_DIALOGFLOW_EVENT).encode('utf-8')
                ).decode('ascii'),
            }
        }
        client = app.test_client()
        response = client.post('/conversation-lifecycle-event', json=payload)
        expected_msg = dict(
            SAMPLE_REDIS_PUBSUB_PUB,
            publish_time='',
            message_id='',
        )
        MockPublish.assert_called_once_with(
            '{0}:{1}'.format(SERVER_ID, CONVERSATION_NAME_WITHOUT_LOCATION),
            json.dumps(expected_msg),
        )
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
