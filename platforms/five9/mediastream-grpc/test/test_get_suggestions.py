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
from google.api_core.exceptions import DeadlineExceeded, Aborted, OutOfRange

# Ensure server & proto modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

# Mock google.auth.default before importing get_suggestions
mock_creds = MagicMock()
mock_creds.universe_domain = "googleapis.com"
with patch("google.auth.default", return_value=(mock_creds, "project_id")):
    from services import get_suggestions


class TestGetSuggestions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.servicer = get_suggestions.VoiceServicer()
        self.profile_patcher = patch("services.get_suggestions.conversation_profile_management")
        self.mock_profile_mgmt = self.profile_patcher.start()

        # Mock conversation profile to avoid network calls
        mock_profile = MagicMock()
        mock_profile.stt_config.language_code = "en-US"
        self.mock_profile_mgmt.get_conversation_profile.return_value = mock_profile

    def tearDown(self):
        self.profile_patcher.stop()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_closes_gracefully(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        # Setup the mock stream to simulate being closed
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = True
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        # Ensure async mocks
        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant
        )

        mock_participant_management.analyze_content_audio_stream = AsyncMock()

        # Setup async request iterator
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

        # Verify we got the handshake
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].status.code, 1001)

        # Verify interactions
        mock_conversation_management.create_conversation.assert_called()
        mock_participant_management.create_participant.assert_called()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_handles_none_response(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        # Setup stream to NOT be closed initially, to enter the loop
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant
        )

        # Mock analyze_content_audio_stream returning empty async iterator
        async def side_effect_close_stream(*args, **kwargs):
            mock_stream_instance.closed = True
            if False:
                yield  # make it an async generator

        mock_participant_management.analyze_content_audio_stream = AsyncMock(
            side_effect=side_effect_close_stream
        )

        # Request iterator
        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"

        async def request_iterator():
            yield mock_config

        context = MagicMock()

        # Run the method (consume generator)
        async for _ in self.servicer.StreamingVoice(request_iterator(), context):
            pass

        # It should verify that analyze_content_audio_stream was called
        mock_participant_management.analyze_content_audio_stream.assert_called()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_with_real_audio(
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
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant
        )

        # Ensure analyze_content_audio_stream closes the stream to prevent infinite loop
        async def side_effect_close_stream(*args, **kwargs):
            mock_stream_instance.closed = True
            if False:
                yield  # make it an async generator

        mock_participant_management.analyze_content_audio_stream = AsyncMock(
            side_effect=side_effect_close_stream
        )

        # Path to audio file
        audio_path = os.path.join(os.path.dirname(__file__), "audio/END_USER.mp3")

        # Generator for requests
        async def request_generator():
            # 1. Config message
            mock_config = MagicMock()
            mock_config.streaming_config.vcc_call_id = "12345"
            mock_config.streaming_config.voice_config.sample_rate_hertz = (
                8000  # Wav file might vary
            )
            mock_config.streaming_config.call_leg = 1
            yield mock_config

            chunk_size = 1024
            if os.path.exists(audio_path):
                with open(audio_path, "rb") as wf:
                    while data := wf.read(chunk_size):
                        req = MagicMock()
                        req.streaming_config = None  # Ensure it's treated as audio
                        req.audio_content = data
                        yield req
            else:
                # Backup if audio file missing in test env
                yield MagicMock(audio_content=b"\0" * 10)

            # Simulate stream end effectively by ending items
            mock_stream_instance.closed = True

        context = MagicMock()

        # Execute
        responses = [
            res
            async for res in self.servicer.StreamingVoice(request_generator(), context)
        ]

        # Assertions
        self.assertGreaterEqual(len(responses), 1)
        self.assertEqual(responses[0].status.code, 1001)

        # Verify backend API was called
        mock_participant_management.analyze_content_audio_stream.assert_called()
        # Verify complete_conversation is called for clean exit
        mock_conversation_management.complete_conversation.assert_called()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_no_completion_on_error(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        # Setup stream with error
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = True
        mock_stream_instance.terminate = True
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = Exception("Stream Error")
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(
            return_value=mock_participant
        )

        # analyze_content returns simple iterator then finishes
        mock_participant_management.analyze_content_audio_stream = AsyncMock(
            return_value=b""
        )

        # Fix mock to return async iterator if needed or list
        # Actually it returns async iterator of responses.
        async def response_gen():
            if False:
                yield

        mock_participant_management.analyze_content_audio_stream.return_value = (
            response_gen()
        )

        # Request iterator
        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"

        async def request_iterator():
            yield mock_config

        context = MagicMock()

        # Run
        async for _ in self.servicer.StreamingVoice(request_iterator(), context):
            pass

        # Verify complete_conversation is NOT called
        mock_conversation_management.complete_conversation.assert_not_called()

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    @patch("services.get_suggestions.time.time")
    async def test_streaming_voice_no_restart_before_threshold(
        self,
        mock_time,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_stream_instance.is_final = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()
        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(return_value=mock_participant)

        mock_time.side_effect = [1000.0, 1000.0, 1005.0, 1005.0]

        mock_response = MagicMock()
        mock_response.recognition_result.is_final = True
        mock_response.recognition_result.speech_end_offset.seconds = 1
        mock_response.recognition_result.speech_end_offset.microseconds = 0

        async def response_gen():
            yield mock_response
            mock_stream_instance.closed = True

        mock_participant_management.analyze_content_audio_stream = AsyncMock(return_value=response_gen())

        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        async def request_iterator():
            yield mock_config

        context = MagicMock()

        with patch("services.get_suggestions.RESTART_THRESHOLD", 10):
            async for _ in self.servicer.StreamingVoice(request_iterator(), context):
                pass

        self.assertFalse(mock_stream_instance.is_final)

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    @patch("services.get_suggestions.time.time")
    async def test_streaming_voice_restarts_after_threshold(
        self,
        mock_time,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_stream_instance.is_final = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()
        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(return_value=mock_participant)

        mock_time.side_effect = [1000.0, 1000.0, 1015.0, 1015.0]

        mock_response = MagicMock()
        mock_response.recognition_result.is_final = True
        mock_response.recognition_result.speech_end_offset.seconds = 1
        mock_response.recognition_result.speech_end_offset.microseconds = 0

        async def response_gen():
            yield mock_response
            mock_stream_instance.closed = True

        mock_participant_management.analyze_content_audio_stream = AsyncMock(return_value=response_gen())

        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        async def request_iterator():
            yield mock_config

        context = MagicMock()

        with patch("services.get_suggestions.RESTART_THRESHOLD", 10):
            async for _ in self.servicer.StreamingVoice(request_iterator(), context):
                pass

        self.assertTrue(mock_stream_instance.is_final)

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_restarts_on_deadline_exceeded(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()
        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(return_value=mock_participant)

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DeadlineExceeded("Timeout")
            else:
                mock_stream_instance.closed = True
                if False:
                    yield

        mock_participant_management.analyze_content_audio_stream = AsyncMock(side_effect=side_effect)

        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        async def request_iterator():
            yield mock_config

        context = MagicMock()

        async for _ in self.servicer.StreamingVoice(request_iterator(), context):
            pass

        self.assertEqual(call_count, 2)

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_restarts_on_aborted(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()
        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(return_value=mock_participant)

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Aborted("Aborted")
            else:
                mock_stream_instance.closed = True
                if False:
                    yield

        mock_participant_management.analyze_content_audio_stream = AsyncMock(side_effect=side_effect)

        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        async def request_iterator():
            yield mock_config

        context = MagicMock()

        async for _ in self.servicer.StreamingVoice(request_iterator(), context):
            pass

        self.assertEqual(call_count, 2)

    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.call_stream.CallStream")
    async def test_streaming_voice_restarts_on_out_of_range(
        self,
        mock_call_stream,
        mock_participant_management,
        mock_conversation_management,
    ):
        mock_stream_instance = MagicMock()
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False
        mock_stream_instance.disconnect_received = False
        mock_stream_instance.error = None
        mock_stream_instance.cancelled = False
        mock_call_stream.return_value.__enter__.return_value = mock_stream_instance

        mock_conversation_management.get_conversation = AsyncMock(return_value=None)
        mock_conversation_management.create_conversation = AsyncMock()
        mock_conversation_management.complete_conversation = AsyncMock()
        mock_participant = MagicMock()
        mock_participant.name = "projects/p/conversations/c/participants/123"
        mock_participant_management.create_participant = AsyncMock(return_value=mock_participant)

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OutOfRange("Out of Range")
            else:
                mock_stream_instance.closed = True
                if False:
                    yield

        mock_participant_management.analyze_content_audio_stream = AsyncMock(side_effect=side_effect)

        mock_config = MagicMock()
        mock_config.streaming_config.vcc_call_id = "12345"
        async def request_iterator():
            yield mock_config

        context = MagicMock()

        async for _ in self.servicer.StreamingVoice(request_iterator(), context):
            pass

        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
