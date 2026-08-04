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
import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure server & proto modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

from utils import call_stream, participant_management

# Import the module under test
# Mock google.auth.default before importing utils to avoid Credential errors
mock_creds = MagicMock()
mock_creds.universe_domain = "googleapis.com"
with patch("google.auth.default", return_value=(mock_creds, "project_id")):
    from utils import participant_management
    from utils import conversation_management


class TestParticipantManagement(unittest.IsolatedAsyncioTestCase):
    @patch("utils.participant_management.dialogflow.ConversationsClient")
    @patch("utils.participant_management.participants_client")
    async def test_create_participant_uses_correct_client_path_helper(
        self, mock_participants_client, mock_conversations_client
    ):
        """Verify proper usage of ConversationsClient for generating conversation path."""
        # Setup
        # Configure the mock client to handle async calls
        mock_participants_client.create_participant = AsyncMock()

        project_id = "test-project"
        conversation_id = "test-conv"
        role = "END_USER"

        expected_path = "projects/test/conversations/test-conv"
        mock_conversations_client.conversation_path.return_value = expected_path

        mock_response = MagicMock()
        mock_response.name = "new_participant"
        mock_participants_client.create_participant.return_value = mock_response

        # Act
        await participant_management.create_participant(
            project_id, conversation_id, role
        )

        # Assert
        # 1. Verify ConversationsClient.conversation_path was used (Fix verification)
        mock_conversations_client.conversation_path.assert_called_with(
            project_id, conversation_id
        )

        # 2. Verify create_participant was called with the correct parent path
        mock_participants_client.create_participant.assert_called_once()
        _, kwargs = mock_participants_client.create_participant.call_args
        self.assertEqual(kwargs["parent"], expected_path)


class TestConversationManagement(unittest.IsolatedAsyncioTestCase):
    @patch("utils.conversation_management.conv_client")
    @patch("utils.conversation_management.profile_client")
    @patch("utils.conversation_management.dialogflow")
    async def test_create_conversation_calls_client(
        self, mock_dialogflow, mock_profile_client, mock_conv_client
    ):
        """Verify create_conversation calls the underlying client correctly."""
        # Setup
        # Configure mock to be awaitable
        mock_conv_client.create_conversation = AsyncMock()

        project_id = "test-project"
        profile_id = "test-profile"
        conversation_id = "test-conv-id"

        profile_path = "projects/test/profiles/test-profile"
        mock_profile_client.conversation_profile_path.return_value = profile_path

        mock_response = MagicMock()
        mock_response.name = "created_conversation"
        mock_conv_client.create_conversation.return_value = mock_response

        # Act
        await conversation_management.create_conversation(
            project_id, profile_id, conversation_id
        )

        # Assert
        # Verify CreateConversationRequest was initialized with correct params
        mock_dialogflow.CreateConversationRequest.assert_called_once()
        _, kwargs = mock_dialogflow.CreateConversationRequest.call_args
        self.assertEqual(kwargs["parent"], f"projects/{project_id}")
        self.assertEqual(kwargs["conversation_id"], conversation_id)
        self.assertEqual(kwargs["conversation"]["conversation_profile"], profile_path)

        mock_conv_client.create_conversation.assert_called_once()


if __name__ == "__main__":
    unittest.main()


class TestCallStream(unittest.IsolatedAsyncioTestCase):
    async def test_generator_handles_cancellation(self):
        """Verify that asyncio.CancelledError is caught and handled gracefully."""
        # Setup

        async def mock_async_generator():
            yield MagicMock(audio_content=b"audio")
            raise asyncio.CancelledError("Stream cancelled")

        input_gen = mock_async_generator()
        conversation_id = "test-conv"
        role = "END_USER"

        # Act
        stream = call_stream.CallStream(
            input_generator=input_gen, conversation_id=conversation_id, role=role
        )

        with stream:
            chunks = []
            async for chunk in stream.generator():
                chunks.append(chunk)

        # Assert
        # The generator should yield the first chunk
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], b"audio")

        # And it should have closed gracefully (no exception raised)
        self.assertTrue(stream.closed)
        self.assertTrue(stream.terminate)


class TestParticipantManagementAnalyzeContent(unittest.IsolatedAsyncioTestCase):
    async def test_analyze_content_handles_cancellation(self):
        """Verify that asyncio.CancelledError is handled within the generator."""
        # Setup
        # We need to mock the stream.generator() to raise CancelledError
        mock_stream = MagicMock()

        async def mock_generator():
            yield b"audio_chunk"
            raise asyncio.CancelledError("Comparison cancelled")

        mock_stream.generator = mock_generator

        # Mock participants client
        with patch(
            "utils.participant_management._get_participants_client"
        ) as mock_get_client:
            mock_client_instance = MagicMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.participant_path.return_value = (
                "projects/p/conversations/c/participants/part"
            )

            # Use side_effect to capture the generator passed to streaming_analyze_content
            # and iterate it to trigger the CancelledError handling inside gen_requests
            async def iterate_requests(*args, **kwargs):
                requests_gen = kwargs["requests"]
                results = []
                async for req in requests_gen:
                    results.append(req)
                return results

            mock_client_instance.bidi_streaming_analyze_content = AsyncMock(side_effect=iterate_requests)

            # Act
            # This should not raise CancelledError because we caught it
            await participant_management.analyze_content_audio_stream(
                project_id="p",
                conversation_id="c",
                participant_id="part",
                sample_rate_hertz=16000,
                stream=mock_stream,
                timeout=10,
                language_code="en-US",
            )

            # Assert
            # Verify stream yielded the first chunk
            # And no exception was raised out of analyze_content_audio_stream
