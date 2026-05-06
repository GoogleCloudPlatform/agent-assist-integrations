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

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure server & proto modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

# Mock google.auth.default before importing get_suggestions
mock_creds = MagicMock()
mock_creds.universe_domain = "googleapis.com"
with patch("google.auth.default", return_value=(mock_creds, "project_id")):
    from services import get_suggestions


class TestReconnect(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.servicer = get_suggestions.VoiceServicer()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_retry_on_500_error(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        # Setup the mock stream
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False

        # Initialize restart_counter
        mock_stream_instance.restart_counter = 0

        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant
        )

        # DEFINE SIDE EFFECT FOR analyze_content_audio_stream
        # First call: Raises 500 Exception
        # Second call: Returns success generator, then sets closed=True to end loop
        async def success_generator():
            yield MagicMock()  # Yield one good response

        async def analyze_side_effect(*args, **kwargs):
            # Access the side effect call count via the mock to decide what to do
            call_count = (
                mock_participant_management.analyze_content_audio_stream.call_count
            )
            if call_count == 1:
                raise Exception("500 Internal error encountered")
            else:
                # Second call - success
                # Set terminate/closed eventually to break loop after this
                # But here we just return the generator.
                # The loop checks stream.closed. We can set it here or rely on the generator yielding.
                # Let's return a generator, and set closed=True when we are done?
                # Actually, in the real code, analyze_content_audio_stream returns, then we yield responses.
                # If we return a generator, the code iterates it.
                mock_stream_instance.closed = (
                    True  # End the loop after this successful call
                )
                return success_generator()

        mock_participant_management.analyze_content_audio_stream.side_effect = (
            analyze_side_effect
        )

        # Request iterator
        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        mock_config.streaming_config.voice_config.sample_rate_hertz = 16000
        mock_config.streaming_config.call_leg = 1

        async def request_iterator():
            yield mock_config

        context = MagicMock()

        # Run the method
        responses = [
            res
            async for res in self.servicer.StreamingVoice(request_iterator(), context)
        ]

        # Assertions
        # 1. We expect analyze_content_audio_stream to be called TWICE (one fail, one retry)
        # If the code breaks on 500, this will fail (called once).
        self.assertEqual(
            mock_participant_management.analyze_content_audio_stream.call_count,
            2,
            "Should retry on 500 error",
        )

        # 2. Verify we got responses (at least the handshake + one success response)
        self.assertGreaterEqual(len(responses), 1)


if __name__ == "__main__":
    unittest.main()
