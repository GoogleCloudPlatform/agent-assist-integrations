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
"""Unit tests for Five9 gRPC retry and reconnection behavior."""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from google.api_core.exceptions import InternalServerError

# Ensure server & proto modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

# Mock google.auth.default before importing get_suggestions
mock_creds = MagicMock()
mock_creds.universe_domain = "googleapis.com"
with patch("google.auth.default", return_value=(mock_creds, "project_id")):
    from services import get_suggestions


class TestReconnect(unittest.IsolatedAsyncioTestCase):
    """Unit tests for reconnection and retry behavior."""

    def setUp(self):
        self.servicer = get_suggestions.VoiceServicer()
        self.token_patcher = patch(
            "services.get_suggestions.FIVE9_TRUST_TOKEN", "test-trust-token")
        self.token_patcher.start()

    def tearDown(self):
        self.token_patcher.stop()

    @patch("services.get_suggestions.conversation_profile_management")
    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_retry_on_500_error(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
        unused_mock_conversation_profile_management,
    ):
        """Tests that stream retries when 500 error is encountered."""
        # Setup the mock stream
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False

        # Initialize restart_counter
        mock_stream_instance.restart_counter = 0

        mock_call_stream.return_value.__enter__.return_value = (
            mock_stream_instance)

        mock_conversation_management.get_conversation = AsyncMock(
            return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant)

        # DEFINE SIDE EFFECT FOR analyze_content_audio_stream
        # First call: Raises 500 Exception
        # Second call: Returns success generator, then sets closed=True
        async def success_generator():
            yield MagicMock()  # Yield one good response

        async def analyze_side_effect(*unused_args, **unused_kwargs):
            # Access call count via mock to decide what to do
            call_count = (mock_participant_management.
                          analyze_content_audio_stream.call_count)
            if call_count == 1:
                raise InternalServerError("Internal error encountered")

            # Second call: return successful response stream and close stream
            mock_stream_instance.closed = True
            return success_generator()

        mock_participant_management.analyze_content_audio_stream.side_effect = (
            analyze_side_effect)

        # Request iterator
        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        mock_config.streaming_config.trust_token = "test-trust-token"
        mock_config.streaming_config.voice_config.sample_rate_hertz = 16000
        mock_config.streaming_config.call_leg = 1

        async def request_iterator():
            yield mock_config

        context = MagicMock()

        # Run the method
        responses = [
            res async for res in self.servicer.StreamingVoice(
                request_iterator(), context)
        ]

        # Assertions
        # 1. We expect analyze_content_audio_stream to be called TWICE
        self.assertEqual(
            mock_participant_management.analyze_content_audio_stream.call_count,
            2,
            "Should retry on 500 error",
        )

        # 2. Verify we got responses
        self.assertGreaterEqual(len(responses), 1)


if __name__ == "__main__":
    unittest.main()
