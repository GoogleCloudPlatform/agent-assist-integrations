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

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Set required environment variables before audiohook_config is loaded
os.environ['API_KEY'] = 'test'
os.environ['CONVERSATION_PROFILE_NAME'] = 'projects/fake-project/locations/global/conversationProfiles/fake-profile'
os.environ['GCP_PROJECT_ID'] = 'fake-project'
os.environ['UI_CONNECTOR'] = 'https://fake-ui-connector'
os.environ['REDISHOST'] = 'localhost'
os.environ['REDISPORT'] = '6379'

# Add current dir to path to import dialogflow_api
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Mock external modules in sys.modules before dialogflow_api is imported
mock_google = MagicMock()
mock_google_auth = MagicMock()
mock_google_auth.default.return_value = (MagicMock(), 'fake-project')
mock_google.auth = mock_google_auth

mock_google_oauth2 = MagicMock()
mock_google.oauth2 = mock_google_oauth2
mock_google_oauth2_id_token = MagicMock()
mock_google_oauth2.id_token = mock_google_oauth2_id_token

mock_requests = MagicMock()

sys.modules['google'] = mock_google
sys.modules['google.auth'] = mock_google_auth
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = mock_google_oauth2
sys.modules['google.oauth2.id_token'] = mock_google_oauth2_id_token
sys.modules['google.api_core'] = MagicMock()
sys.modules['google.api_core.client_options'] = MagicMock()
sys.modules['google.api_core.exceptions'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.dialogflow_v2beta1'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['audio_stream'] = MagicMock()
sys.modules['requests'] = mock_requests

import dialogflow_api


class TestDialogflowAPI(unittest.TestCase):

    @patch('requests.post')
    @patch('google.oauth2.id_token.fetch_id_token')
    def test_store_conversation_mapping_success(self, mock_fetch_id_token, mock_post):
        mock_fetch_id_token.return_value = 'fake_id_token'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dialogflow_api.store_conversation_mapping('fake_integration_key', 'fake_conversation_name')

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json'], {
            'conversationIntegrationKey': 'fake_integration_key',
            'conversationName': 'fake_conversation_name'
        })
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer fake_id_token')

    @patch('dialogflow_api.logging.warning')
    def test_store_conversation_mapping_empty_key(self, mock_warning):
        dialogflow_api.store_conversation_mapping('', 'fake_conversation_name')
        mock_warning.assert_called_with("Cannot store mapping with empty key or conversation name.")

    @patch('requests.post', side_effect=Exception("Connection refused"))
    @patch('google.oauth2.id_token.fetch_id_token', return_value='fake_id_token')
    @patch('dialogflow_api.logging.error')
    def test_store_conversation_mapping_http_error(self, mock_log_error, mock_token, mock_post):
        dialogflow_api.store_conversation_mapping('fake_key', 'fake_name')
        mock_log_error.assert_called()

    def test_determine_dialogflow_api_endpoint(self):
        self.assertEqual(
            dialogflow_api.determine_dialogflow_api_endpoint('global'),
            'dialogflow.googleapis.com'
        )
        self.assertEqual(
            dialogflow_api.determine_dialogflow_api_endpoint('us-central1'),
            'us-central1-dialogflow.googleapis.com'
        )

    def test_create_conversation_name(self):
        conv_name = dialogflow_api.create_conversation_name(
            'conv-123', 'global', 'fake-project'
        )
        self.assertEqual(
            conv_name,
            'projects/fake-project/locations/global/conversations/conv-123'
        )

    def test_determine_conversation_name_without_location(self):
        self.assertEqual(
            dialogflow_api.determine_conversation_name_without_location(
                'projects/p/locations/global/conversations/c'
            ),
            'projects/p/conversations/c'
        )
        self.assertEqual(
            dialogflow_api.determine_conversation_name_without_location(
                'projects/p/conversations/c'
            ),
            'projects/p/conversations/c'
        )


    @patch('dialogflow_api.logging.warning')
    def test_store_conversation_mapping_empty_name(self, mock_warning):
        dialogflow_api.store_conversation_mapping('fake_key', '')
        mock_warning.assert_called_with("Cannot store mapping with empty key or conversation name.")

    @patch('requests.post')
    @patch('google.oauth2.id_token.fetch_id_token', side_effect=Exception("Metadata server unavailable"))
    @patch('dialogflow_api.logging.warning')
    def test_store_conversation_mapping_id_token_failure(self, mock_warning, mock_token, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dialogflow_api.store_conversation_mapping('fake_key', 'fake_name')
        mock_warning.assert_called()
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        # Should proceed without Authorization header if token fetch fails
        self.assertNotIn('Authorization', kwargs['headers'])

    def test_find_participant_by_role(self):
        mock_p1 = MagicMock()
        mock_p1.role = 'HUMAN_AGENT'
        mock_p2 = MagicMock()
        mock_p2.role = 'END_USER'

        participants = [mock_p1, mock_p2]

        found_agent = dialogflow_api.find_participant_by_role('HUMAN_AGENT', participants)
        self.assertEqual(found_agent, mock_p1)

        found_user = dialogflow_api.find_participant_by_role('END_USER', participants)
        self.assertEqual(found_user, mock_p2)

        found_none = dialogflow_api.find_participant_by_role('AUTOMATED_AGENT', participants)
        self.assertIsNone(found_none)


if __name__ == '__main__':
    unittest.main()


