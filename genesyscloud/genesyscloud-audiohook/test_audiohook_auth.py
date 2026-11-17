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
"""Unit tests for Genesys AudioHook WebSocket /connect X-API-KEY authentication."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

os.environ.setdefault("API_KEY", "test-audiohook-api-key")
os.environ.setdefault(
    "CONVERSATION_PROFILE_NAME",
    "projects/test-proj/locations/global/conversationProfiles/test-prof",
)
os.environ.setdefault("GCP_PROJECT_ID", "test-proj")
os.environ.setdefault("UI_CONNECTOR", "https://ui-connector.example")
os.environ.setdefault("REDISHOST", "127.0.0.1")
os.environ.setdefault("REDISPORT", "6379")

mock_flask_sock = MagicMock()
mock_flask_sock.Sock.return_value.route.side_effect = (
    lambda *a, **kw: (lambda f: f))
sys.modules.setdefault("numpy", MagicMock())
sys.modules.setdefault("flask_sock", mock_flask_sock)
sys.modules.setdefault("simple_websocket", MagicMock())
sys.modules.setdefault("dialogflow_api", MagicMock())

import audiohook_blueprint  # pylint: disable=wrong-import-position


class TestAudiohookConnectAuth(unittest.TestCase):
    """Tests X-API-KEY enforcement on /connect."""

    def setUp(self):
        self.app = Flask(__name__)

    @patch("audiohook_blueprint.run_audiohook_connection")
    def test_connect_rejects_missing_api_key(self, mock_run):
        """Closes WebSocket with 1008 when X-API-KEY header is missing."""
        ws = MagicMock()
        with self.app.test_request_context("/connect"):
            audiohook_blueprint.audiohook_connect(ws)
        ws.close.assert_called_once_with(reason=1008, message="invalid api key")
        mock_run.assert_not_called()

    @patch("audiohook_blueprint.run_audiohook_connection")
    def test_connect_rejects_invalid_api_key(self, mock_run):
        """Closes WebSocket with 1008 when X-API-KEY header does not match."""
        ws = MagicMock()
        with self.app.test_request_context(
                "/connect", headers={"X-API-KEY": "wrong-key"}):
            audiohook_blueprint.audiohook_connect(ws)
        ws.close.assert_called_once_with(reason=1008, message="invalid api key")
        mock_run.assert_not_called()

    @patch("audiohook_blueprint.run_audiohook_connection")
    def test_connect_allows_valid_api_key(self, mock_run):
        """Proceeds to run_audiohook_connection when X-API-KEY matches."""
        ws = MagicMock()
        with self.app.test_request_context(
                "/connect", headers={"X-API-KEY": "test-audiohook-api-key"}):
            audiohook_blueprint.audiohook_connect(ws)
        ws.close.assert_not_called()
        mock_run.assert_called_once_with(ws)


if __name__ == "__main__":
    unittest.main()
