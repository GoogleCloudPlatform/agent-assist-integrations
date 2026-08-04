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

"""Module for managing Dialogflow participants."""

import logging
import asyncio


from google.cloud import dialogflow_v2beta1 as dialogflow

ROLES = ["HUMAN_AGENT", "AUTOMATED_AGENT", "END_USER"]

# Initialize client once at the module level for resource efficiency in Cloud Run
participants_client = None


def _get_participants_client():
    global participants_client
    if participants_client is None:
        participants_client = dialogflow.ParticipantsAsyncClient()
    return participants_client


async def create_participant(project_id: str, conversation_id: str, role: str):
    """Creates a participant in a given conversation.

    Args:
        project_id: The GCP project linked with the conversation profile.
        conversation_id: Id of the conversation.
        participant: participant to be created."""

    if role not in ROLES:
        logging.debug(
            f"[{conversation_id}][{role}] Create participant request for unsupported role."
        )
        return None

    conversation_path = dialogflow.ConversationsClient.conversation_path(
        project_id, conversation_id
    )

    try:
        response = await _get_participants_client().create_participant(
            parent=conversation_path, participant={"role": role}, timeout=60
        )

        return response
    except Exception as e:
        logging.error(f"[{conversation_id}][{role}] Create Participant Error: {e}")

        return None


async def analyze_content_audio_stream(
    project_id: str,
    conversation_id: str,
    participant_id: str,
    sample_rate_hertz: int,
    stream,
    timeout: int,
    language_code: str,
    single_utterance=False,
):
    """Stream audio streams to Dialogflow and receive transcripts and
    suggestions.

    Args:
        conversation_id: Id of the conversation.
        participant_id: Id of the participant.
        sample_rate_hertz: hertz rate of the sample.
        stream: the stream to process. It should have generator() method to
          yield input_audio.
        timeout: the timeout of one stream.
        language_code: the language code of the audio. Example: en-US
        single_utterance: whether to use single_utterance.
    """

    participant_name = _get_participants_client().participant_path(
        project_id, conversation_id, participant_id
    )

    async def gen_requests():
        """Generates requests for streaming."""
        # First message must contain participant and config
        yield dialogflow.BidiStreamingAnalyzeContentRequest(
            config={
                "participant": participant_name,
                "voice_session_config": {
                    "input_audio_encoding": dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                    "input_audio_sample_rate_hertz": sample_rate_hertz,
                },
            }
        )

        audio_generator = stream.generator()
        if audio_generator is None:
            logging.error(
                f"[{conversation_id}] analyze_content_audio_stream - audio_generator is None!"
            )
            return

        try:
            async for content in audio_generator:
                if content:
                    yield dialogflow.BidiStreamingAnalyzeContentRequest(
                        input={"audio": content},
                    )
        except asyncio.CancelledError:
            logging.info(
                f"[{conversation_id}] analyze_content_audio_stream - stream cancelled"
            )
        except Exception as e:
            logging.error(
                f"[{conversation_id}] analyze_content_audio_stream - audio_generator error: {e}"
            )

    return await _get_participants_client().bidi_streaming_analyze_content(
        requests=gen_requests(), timeout=timeout
    )
