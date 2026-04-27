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
from unittest.mock import MagicMock, patch, call
import os
import sys

# Append path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

# Mock dependencies before import
with patch.dict(os.environ, {"PROJECT_ID": "test-project"}):
    sys.modules["google"] = MagicMock()
    sys.modules["google.cloud"] = MagicMock()
    sys.modules["grpc"] = MagicMock()
    sys.modules["voice_pb2"] = MagicMock()

    # Mock voice_pb2_grpc with a proper base class for inheritance
    mock_grpc_module = MagicMock()

    class MockBaseVoiceServicer:
        def StreamingVoice(self, request_iterator, context):
            pass  # Base implementation does nothing

    mock_grpc_module.VoiceServicer = MockBaseVoiceServicer
    sys.modules["voice_pb2_grpc"] = mock_grpc_module

    sys.modules["dotenv"] = MagicMock()
    sys.modules["google.api_core"] = MagicMock()

    mock_exceptions = MagicMock()

    class MockDeadlineExceeded(Exception):
        pass

    mock_exceptions.DeadlineExceeded = MockDeadlineExceeded
    sys.modules["google.api_core.exceptions"] = mock_exceptions

    from services import get_suggestions


class TestSuggestionLogging(unittest.TestCase):
    @patch("services.get_suggestions.conversation_management")
    @patch("services.get_suggestions.participant_management")
    @patch("services.get_suggestions.CallStream")
    @patch("services.get_suggestions.logging")
    def test_suggestion_logging(
        self, mock_logging, mock_call_stream, mock_part_mgmt, mock_conv_mgmt
    ):
        # Setup mocks
        mock_servicer = get_suggestions.VoiceServicer()

        # Mock Conversation/Participant creation
        mock_conv_mgmt.create_conversation.return_value = (
            "projects/p/locations/l/conversations/c"
        )
        p_obj = MagicMock()
        p_obj.name = "projects/p/locations/l/conversations/c/participants/p"
        mock_part_mgmt.create_participant.return_value = p_obj

        # Create mock responses for each type

        # 1. Article
        article_resp = MagicMock()
        article = MagicMock()
        article.title = "Test Article"
        article.uri = "http://test.com"
        article_resp.human_agent_suggestion_results = [
            MagicMock(
                suggest_articles_response=MagicMock(articles=[article]),
                suggest_smart_replies_response=None,
                suggest_knowledge_assist_response=None,
            )
        ]
        article_resp.recognition_result.is_final = False

        # 2. Smart Reply
        reply_resp = MagicMock()
        reply = MagicMock()
        reply.reply = "Hello there"
        reply_resp.human_agent_suggestion_results = [
            MagicMock(
                suggest_articles_response=None,
                suggest_smart_replies_response=MagicMock(smart_replies=[reply]),
                suggest_knowledge_assist_response=None,
            )
        ]
        reply_resp.recognition_result.is_final = False

        # 3. Knowledge Assist
        knowledge_resp = MagicMock()
        knowledge_resp.human_agent_suggestion_results = [
            MagicMock(
                suggest_articles_response=None,
                suggest_smart_replies_response=None,
                suggest_knowledge_assist_response=MagicMock(
                    knowledge_assist_answer=MagicMock(
                        suggested_query_answer=MagicMock(
                            answer_text="This is the answer"
                        )
                    )
                ),
            )
        ]
        knowledge_resp.recognition_result.is_final = True  # End stream

        # Setup mock stream to allow loop
        mock_stream_instance = mock_call_stream.return_value
        mock_stream_instance.__enter__.return_value = mock_stream_instance
        # MagicMock attributes are Truthy (mocks), so we must explicitly set them to False
        # to enter the 'while not stream.closed' and 'while not stream.terminate' loops.
        mock_stream_instance.closed = False
        mock_stream_instance.terminate = False

        # Mock analyze_content_audio_stream to return our responses first, then raise exception to break loop
        mock_part_mgmt.analyze_content_audio_stream.side_effect = [
            [article_resp, reply_resp, knowledge_resp],
            Exception("Stop Loop"),
        ]

        # Mock request iterator with explicit config
        req = MagicMock()
        req.streaming_config = MagicMock()
        req.streaming_config.vcc_call_id = 1
        req.streaming_config.voice_config.sample_rate_hertz = 8000
        req.streaming_config.call_leg = 1

        request_iterator = iter([req])
        context = MagicMock()

        # Run the method
        gen = mock_servicer.StreamingVoice(request_iterator, context)
        # Consume generator and store keys
        yielded_responses = []
        try:
            for r in gen:
                yielded_responses.append(r)
        except Exception as e:
            if str(e) != "Stop Loop":
                raise e
            # Expected "Stop Loop" exception from side_effect

        print(f"DEBUG: Yielded: {yielded_responses}")

        # Verify logging calls
        # First verify that analyze_content_audio_stream was actually called
        print(
            f"DEBUG: analyze_content_audio_stream calls: {mock_part_mgmt.analyze_content_audio_stream.call_count}"
        )
        mock_part_mgmt.analyze_content_audio_stream.assert_called()

        # We look for specific calls in the mock_logging.info history

        # Check Article
        self.assertIn(
            call("Article Suggestion: Test Article - http://test.com"),
            mock_logging.info.mock_calls,
        )

        # Check Smart Reply
        self.assertIn(call("Smart Reply: Hello there"), mock_logging.info.mock_calls)

        # Check Knowledge Assist
        self.assertIn(
            call("Knowledge Answer: This is the answer"), mock_logging.info.mock_calls
        )


if __name__ == "__main__":
    unittest.main()
