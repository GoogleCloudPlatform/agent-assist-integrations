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

"""Module for interacting with Agent Assist Backend using
dialogflow_v2beta1 API version
Reference: https://cloud.google.com/python/docs/reference/dialogflow/latest/google.cloud.dialogflow_v2beta1
"""
import logging
import re
import time

import google.auth
import redis
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import FailedPrecondition, OutOfRange, ResourceExhausted
from google.cloud import dialogflow_v2beta1 as dialogflow

from audio_stream import Stream
from audiohook_config import config

# Wait for 2 units of 0.5 second for the redis client to set conversation name
AWAIT_REDIS_COUNTER = 2
AWAIT_REDIS_SECOND_PER_COUNTER = 0.5
LOCATION_ID_REGEX = r"^projects\/[^/]+\/locations\/([^/]+)"

credentials, project = google.auth.default()
redis_client = redis.StrictRedis(
    host=config.redis_host, port=config.redis_port)


try:
    location_id = re.match(
        LOCATION_ID_REGEX, config.conversation_profile_name)[1]
except Exception as e:
    raise ValueError(
        "Conversation profile name is not in correct format") from e


def determine_dialogflow_api_endpoint(location: str) -> str:
    """Get Dialogflow api endpoint
    Reference: https://cloud.google.com/dialogflow/es/docs/reference/rest/v2-overview#service-endpoint
    """
    dialogflow_endpoint = "dialogflow.googleapis.com"
    if location != 'global':
        dialogflow_endpoint = f"{location}-dialogflow.googleapis.com"
    logging.debug("Dialogflow api endpoint %s", dialogflow_endpoint)
    return dialogflow_endpoint


def create_conversation_name(conversation_id: str, location_id: str, project: str) -> str:
    """Set conversation name for the object
    """
    return f"projects/{project}/locations/{location_id}/conversations/{conversation_id}"


def find_participant_by_role(role: dialogflow.Participant.Role, participants_list: list[dialogflow.Participant]) -> dialogflow.Participant | None:

    for participant in participants_list:
        if participant.role == role:

            logging.debug("the active participant is %s:%s ",
                          participant.role, participant.name)
            return participant

    return None


class DialogflowAPI:
    """Class for interacting with the Dialogflow API
    """

    def __init__(self) -> None:

        self.api_endpoint = determine_dialogflow_api_endpoint(
            location_id)
        self.participants_client = dialogflow.ParticipantsClient(
            credentials=credentials,
            client_options=ClientOptions(
                api_endpoint=self.api_endpoint)
        )
        self.conversations_client = dialogflow.ConversationsClient(
            credentials=credentials,
            client_options=ClientOptions(
                api_endpoint=self.api_endpoint
            )
        )
        self.conversation_profiles_client = dialogflow.ConversationProfilesClient(
            credentials=credentials, client_options=ClientOptions(
                api_endpoint=self.api_endpoint))

    def get_conversation_profile(
            self,
            conversation_profile_name: str) -> dialogflow.ConversationProfile:
        """Load conversation profile
        """
        logging.debug("Getting conversation profile for %s ",
                      conversation_profile_name)
        return self.conversation_profiles_client.get_conversation_profile(
            request=dialogflow.GetConversationProfileRequest(
                name=conversation_profile_name
            )
        )

    def create_conversation(
            self,
            conversation_profile: dialogflow.ConversationProfile,
            conversation_id: str,
    ) -> dialogflow.Conversation:
        """Create conversation using conversation_id
        """
        conversation = dialogflow.Conversation(
            conversation_profile=conversation_profile.name
        )
        project_path = self.conversations_client.common_location_path(
            project, location_id)
        conversation_request = dialogflow.CreateConversationRequest(
            parent=project_path,
            conversation=conversation,
            conversation_id=conversation_id,
        )

        conversation = self.conversations_client.create_conversation(
            request=conversation_request)

        logging.info(
            "Created conversation %s for project path %s", conversation.name,
            project_path)

        return conversation

    def get_conversation(
            self, conversation_name: str) -> dialogflow.Conversation:
        """Get conversation using the conversation_name from dialogflow
        """

        get_conversation_request = dialogflow.GetConversationRequest(
            name=conversation_name,
        )

        conversation = self.conversations_client.get_conversation(
            request=get_conversation_request)

        return conversation

    def list_participant(self,
                         conversation_name: str) -> list[dialogflow.Participant]:
        """List existing participant for Human agent and End user

        Args:
            conversation_name (str): conversation name

        Returns:
            _type_: _description_
        """
        participants_pagers = self.participants_client.list_participants(
            dialogflow.ListParticipantsRequest(parent=conversation_name))
        participant_list = list(participants_pagers.__iter__())
        logging.debug("participant list %s, type ", participant_list)
        return participant_list

    def create_participant(
            self, conversation_name: str,
            role: str):
        """Create both the agent and customer participant for the conversation

        Args:
            conversation_id (str): conversation id from the websocket message parameters
        """
        participant = dialogflow.Participant()
        participant.role = role
        participant = self.participants_client.create_participant(
            parent=conversation_name, participant=participant)
        logging.debug("Creating new participant %s:%s",
                      role,
                      participant)

        return participant

    def maintained_streaming_analyze_content(
            self,
            audio_stream: Stream,
            participant: dialogflow.Participant,
            audio_config: dialogflow.InputAudioConfig):
        """While the stream is not closed or terminated, maintain a steady call to streaming
        analyze content API endpoint
        """
        logging.debug("Call streaming analyze content %s, %s",
                      audio_stream.closed, audio_stream.is_final)
        while not audio_stream.terminate:
            # while not audio_stream.is_final and not audio_stream.closed:
            while not audio_stream.closed:
                self.streaming_analyze_content(
                    audio_stream,
                    participant,
                    audio_config)

    def streaming_analyze_content(
            self,
            audio_stream: Stream,
            participant: dialogflow.Participant,
            audio_config: dialogflow.InputAudioConfig):
        """Call dialogflow backend StreamingAnalyzeContent endpoint,
        and send the audio binary stream from Audiohook.
        """
        try:
            logging.debug("call streaming analyze content for %s", participant)
            responses = self.participants_client.streaming_analyze_content(
                requests=self.generator_streaming_analyze_content_request(
                    audio_config, participant, audio_stream))
            for response in responses:
                audio_stream.speech_end_offset = response.recognition_result.speech_end_offset.seconds * 1000
                logging.debug(response)
                if response.recognition_result.is_final:
                    audio_stream.is_final = True
                    logging.debug(
                        "Final transcript for %s: %s, and is final offset",
                        participant.role.name,
                        response.recognition_result.transcript,
                    )
                    offset = response.recognition_result.speech_end_offset
                    audio_stream.is_final_offset = int(
                        offset.seconds * 1000 + offset.microseconds / 1000
                    )
                if response.recognition_result:
                    logging.debug(
                        "Role %s: Interim response recognition result transcript: %s, time %s",
                        participant.role.name,
                        response.recognition_result.transcript,
                        response.recognition_result.speech_end_offset)
        except OutOfRange as e:
            logging.warning(
                "The single audio stream exceeded maximum duration restrictions %s ", e)
            # return to restart the stream.
            return
        except FailedPrecondition as e:
            audio_stream.closed = True
            logging.warning(
                "Failed the precondition check for StreamingAnalyzeContent %s ", e)
            return
        except ResourceExhausted as e:
            audio_stream.closed = True
            logging.warning(
                "Exceed quota for calling streaming analyze content %s ", e)
            return
    def complete_conversation(self, conversation_name: str):
        """Send complete conversation request to Dialogflow
        """
        self.conversations_client.complete_conversation(
            name=conversation_name
        )
        logging.debug("Call complete conversation for %s", conversation_name)

    def generator_streaming_analyze_content_request(
            self,
            audio_config: dialogflow.InputAudioConfig,
            participant: dialogflow.Participant,
            audio_stream: Stream):
        """Generates and return an iterator for StreamingAnalyzeContentRequest,
        The first request should only include the input_audio_config
        And the following request contains the audio chunks as input_audio.
        The last request does not have any input_audio or input_audio_config and indicates that
        the server side is half-closing the streaming

        Args:
            audio_config (dialogflow.InputAudioConfig): Input for Speech Recognizer
            https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/InputAudioConfig
            participant (dialogflow.Participant): Participant for the Dialogflow API call
            audio_queue (asyncio.Queue): Queue to store the audio binary stream

        Yields:
            _type_: first filed the audio config, and then yield the binary data.
        """
        # Sending audio_config for participant
        enable_debugging_info = config.log_level.upper() == "DEBUG"
        generator = audio_stream.generator()
        yield dialogflow.StreamingAnalyzeContentRequest(
            participant=participant.name,
            audio_config=audio_config,
            enable_debugging_info=enable_debugging_info,
            output_multiple_utterances=True,
        )

        for content in generator:
            # next audio chunks to streaming_analyze_content
            yield dialogflow.StreamingAnalyzeContentRequest(
                input_audio=content,
                enable_debugging_info=enable_debugging_info,
                output_multiple_utterances=True,
            )

        logging.info(
            "Participant: %s, streaming analyze content request, end streaming yield an empty request ",
            participant.name)
        yield dialogflow.StreamingAnalyzeContentRequest(
            enable_debugging_info=enable_debugging_info,
        )
        logging.debug(
            "Ending the current audio stream session, start new session")


def await_redis(conversation_name: str) -> bool:
    """Check if the redis memory store connection has been established or not
    """
    conversation_name = determine_conversation_name_without_location(
        conversation_name)
    # give the user bit time to accept the call and wait for the Agent Assist Backend
    # to create the redis memory store
    counter = AWAIT_REDIS_COUNTER

    redis_exists = redis_client.exists(conversation_name) != 0
    while not redis_exists and counter > 0:
        time.sleep(AWAIT_REDIS_SECOND_PER_COUNTER)
        redis_exists = redis_client.exists(conversation_name) != 0
        counter = counter - 1
    logging.debug("return to send resume message redis client exist %s and final counter %s ",
                  redis_exists, counter)
    return redis_exists


def determine_conversation_name_without_location(conversation_name: str):
    """Returns a conversation name without its location id."""
    conversation_name_without_location = conversation_name
    if '/locations/' in conversation_name:
        name_array = conversation_name.split('/')
        conversation_name_without_location = '/'.join(
            name_array[i] for i in [0, 1, -2, -1])
    return conversation_name_without_location
