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
"""Unit tests for Five9 MediaStream HTTP service authentication."""

import hashlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("dotenv", MagicMock())
os.environ.setdefault("FIVE9_TRUST_TOKEN", "test-five9-trust-token")
os.environ.setdefault("FIVE9_API_KEY", "test-five9-api-key")

import main  # pylint: disable=wrong-import-position


class TestFive9MediastreamHttp(unittest.TestCase):
    """Tests API key enforcement on Five9 HTTP endpoints."""

    def setUp(self):
        self.client = main.app.test_client()

    def test_ui_modules_rejects_missing_api_key(self):
        """Rejects GET /agent-assist-ui-modules/ without x-api-key header."""
        response = self.client.get("/agent-assist-ui-modules/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "Unauthorized"})

    def test_ui_modules_rejects_invalid_api_key(self):
        """Rejects GET /agent-assist-ui-modules/ with wrong x-api-key header."""
        response = self.client.get(
            "/agent-assist-ui-modules/",
            headers={"x-api-key": "wrong-key"},
        )
        self.assertEqual(response.status_code, 401)

    @patch("main.requests.post")
    def test_ui_modules_allows_valid_api_key(self, mock_post):
        """Renders UI modules page when valid x-api-key header is provided."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"token": "minted-jwt"}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ,
                        {"UI_CONNECTOR_URL": "https://ui-connector.example"}):
            response = self.client.get(
                "/agent-assist-ui-modules/",
                headers={"x-api-key": "test-five9-api-key"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"minted-jwt", response.data)

    def test_cti_event_rejects_omitted_api_key(self):
        """Rejects /cti-call-event-destination/ when x-api-key is omitted."""
        get_resp = self.client.get("/cti-call-event-destination/")
        self.assertEqual(get_resp.status_code, 401)

        post_resp = self.client.post(
            "/cti-call-event-destination/",
            json={"payload": {}},
        )
        self.assertEqual(post_resp.status_code, 401)

    def test_cti_event_allows_valid_api_key(self):
        """Returns SHA256(FIVE9_TRUST_TOKEN) when x-api-key is valid."""
        response = self.client.get(
            "/cti-call-event-destination/",
            headers={"x-api-key": "test-five9-api-key"},
        )
        self.assertEqual(response.status_code, 200)
        expected_hash = hashlib.sha256(b"test-five9-trust-token").hexdigest()
        self.assertEqual(response.get_json(), expected_hash)


if __name__ == "__main__":
    unittest.main()
