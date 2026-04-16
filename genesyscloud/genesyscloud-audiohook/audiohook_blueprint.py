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

""" Module for receiving audio streaming from Audiohook Monitor and
call Agent Assist backend
"""
import json
import logging
from dataclasses import dataclass, field
from threading import Thread

import numpy as np
from flask import Blueprint
from flask_sock import Sock
from google.api_core.exceptions import NotFound
from google.cloud import dialogflow_v2beta1 as dialogflow
from simple_websocket import Server

from audio_stream import Stream
from audiohook import DEFAULT_CONVERSATION_ID, AudioHook
from audiohook_config import config
from dialogflow_api import (DialogflowAPI, await_redis, create_conversation_name,
                            find_participant_by_role, location_id, project)

audiohook_bp = Blueprint("audiohook", __name__)
sock = Sock(audiohook_bp)


logging.getLogger()
logging.basicConfig(
    format='%(levelname)-8s [%(filename)s:%(lineno)d in '
           'function %(funcName)s] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=config.log_level.upper()
)


@dataclass
class OpenConversationState:
    """ Memorize the state after open message that is not a connection prob
    """
    agent_thread: Thread
    user_thread: Thread
    conversation_name: str
    is_opened: bool


def process_open_conversation_message(
        conversation_id: str,
        dialogflow_api: DialogflowAPI,
        agent_stream: Stream,
        customer_stream: Stream,
        ws: Server,
        audiohook: AudioHook
) -> OpenConversationState:
    """Process "open" message get from Audiohook Monitor, and establish a state
    object for conversation_name, agent_thread, user_thread, and is_opened bool
    """

    conversation_profile = dialogflow_api.get_conversation_profile(
        conversation_profile_name=config.conversation_profile_name)
    agent_audio_config = agent_stream.define_audio_config(conversation_profile)
    customer_audio_config = customer_stream.define_audio_config(
        conversation_profile)
    normalized_conversation_id = 'a' + conversation_id
    conversation_name = create_conversation_name(
        normalized_conversation_id, location_id, project)
    try:
        dialogflow_api.get_conversation(
            conversation_name)
    except NotFound as e:
        logging.warning("Error getting the conversation : %s", e)
        dialogflow_api.create_conversation(
            conversation_profile, normalized_conversation_id)

    try:
        participants_list = dialogflow_api.list_participant(
            conversation_name)
        participant_agent = find_participant_by_role(
            dialogflow.Participant.Role.HUMAN_AGENT, participants_list)
        participant_user = find_participant_by_role(
            dialogflow.Participant.Role.END_USER, participants_list)
        if not participant_agent:
            participant_agent = dialogflow_api.create_participant(
                conversation_name=conversation_name, role="HUMAN_AGENT")
        if not participant_user:
            participant_user = dialogflow_api.create_participant(
                conversation_name=conversation_name, role="END_USER")
    except NotFound as e:
        logging.error("Participants not found %s: ", e)

    agent_thread = Thread(
        target=dialogflow_api.maintained_streaming_analyze_content, args=(
            agent_stream, participant_agent, agent_audio_config))
    user_thread = Thread(
        target=dialogflow_api.maintained_streaming_analyze_content, args=(
            customer_stream, participant_user, customer_audio_config))
    ws.send(json.dumps(audiohook.create_opened_message()))
    return OpenConversationState(
        agent_thread,
        user_thread,
        conversation_name,
        True)


def process_ongoing_conversation_messages(
        message: json,
        dialogflow_api: DialogflowAPI,
        audiohook: AudioHook,
        agent_stream: Stream,
        customer_stream: Stream,
        open_conversation_state: OpenConversationState,
        ws: Server) -> bool:
    """Process string messages that are not "open" and "ping" from Audiohook client through websocket.

    Note:
        Audiohook client passes Null UUIDs (00000000-0000-0000-0000-000000000000)
        as conversationId and participant.id parameters to identify connection probes.
        https://developer.genesys.cloud/devapps/audiohook/protocol-reference#openparameters

    Reference: https://developer.genesys.cloud/devapps/audiohook/protocol-reference

    Return:
        True, if there is a connection close message. So the outer loop for
        receiving audio can be completed
        False, for other messages to continue process messages from websocket
    """
    message_type = message.get("type")
    match message_type:
        case "resumed":
            # The first paused message after open message sets the
            # closed to True, now after resume, need to flip the bit
            customer_stream.closed = False
            agent_stream.closed = False
            open_conversation_state.agent_thread.start()
            open_conversation_state.user_thread.start()
        case "paused":
            customer_stream.closed = True
            agent_stream.closed = True
            logging.debug("Audio stream is paused")
        case "close":
            # This "close" is for ending a real conversation
            agent_stream.closed = True
            customer_stream.closed = True
            agent_stream.terminate = True
            customer_stream.terminate = True
            ws.send(json.dumps(audiohook.create_close_message()))
            try:
                dialogflow_api.complete_conversation(
                    open_conversation_state.conversation_name)
            except Exception as e:
                logging.error("Error completing conversation %s", e)
            # wait for the two thread to finish then terminate
            logging.debug("Stop streaming threads for customers and agents")
            return True
        case "discarded":
            start_time = message.get("START_TIME")
            duration = message.get("DURATION")
            logging.info(
                "Currently the audio stream has been paused from %s for about %s second",
                start_time,
                duration)
    return False


def wait_for_redis_resume(open_conversation_state: OpenConversationState,
                          audiohook: AudioHook, ws: Server):
    await_redis(
            open_conversation_state.conversation_name)
    # Always send the resume after awaiting the redis, don't stop the audio streaming
    # event if redis client is not set
    ws.send(json.dumps(audiohook.create_resume_message()))


@sock.route('/connect')
def audiohook_connect(ws: Server):
    """Genesys Cloud Audiohook connector

    Args:
        ws (Server): Websocket server for exchange messages
    """
    agent_stream = Stream(
        config.rate, chunk_size=config.chunk_size)
    customer_stream = Stream(
        config.rate, chunk_size=config.chunk_size)

    dialogflow_api = DialogflowAPI()
    audiohook = AudioHook()
    logging.info(
        "Audiohook client connected with the interceptor server")
    open_conversation_state = None
    while True:
        data = ws.receive()
        if isinstance(data, str):
            try:
                json_message = json.loads(data)
            except ValueError as e:
                logging.warning(
                    "Not a valid JSON message %s, error details %s ", data, e)
                continue
            message_type = json_message.get("type")
            logging.info(
                "Handle %s message %s", message_type, json_message)
            conversation_id = json_message.get("parameters", {}).get(
                "conversationId", DEFAULT_CONVERSATION_ID)
            audiohook.set_session_id(json_message.get("id", 0))
            audiohook.set_client_sequence(json_message.get("seq"))
            if message_type == "open":
                if conversation_id == DEFAULT_CONVERSATION_ID:
                    logging.debug(
                        "Connection Probe, not creating Dialogflow Conversation")
                    ws.send(json.dumps(audiohook.create_opened_message()))
                elif conversation_id != DEFAULT_CONVERSATION_ID and open_conversation_state is None:
                    # Get the first "open" message for real conversation
                    # open_state contains the agent and user thread for
                    # calling streaming_analyze_content
                    # a bool flag indicating if conversation, participants have been initialized
                    # and the conversation_name for the dialogflow.Conversation object
                    open_conversation_state = process_open_conversation_message(
                        conversation_id,
                        dialogflow_api,
                        agent_stream,
                        customer_stream,
                        ws,
                        audiohook,
                    )
                    logging.debug(
                        "open conversation message %s ", open_conversation_state)
                    # Check if the redis client has join_room called from the
                    # agent assist backend. Before setting conversation_name in the redis client,
                    # we should not publish any messages to the redis client
                    # otherwise e UI modules will not receive pub/subs until redis connects the conversation
                    await_redis_thread = Thread(target=wait_for_redis_resume, args=(
                        open_conversation_state, audiohook, ws))
                    await_redis_thread.start()
            elif message_type == "ping":
                ws.send(json.dumps(audiohook.create_pong_message()))
            elif message_type == "close" and open_conversation_state is None:
                # This "close" is for a connection prob, we don't need to call dialogflow
                # to complete conversation and terminate the stream in this case
                ws.send(json.dumps(audiohook.create_close_message()))
                break
            elif open_conversation_state is not None:
                # Close websocket connection when receive a "close message"
                if (process_ongoing_conversation_messages(json_message,
                                                          dialogflow_api,
                                                          audiohook,
                                                          agent_stream,
                                                          customer_stream,
                                                          open_conversation_state, ws,
                                                          )):
                    logging.info(
                        "Disconnecting Audiohook with the server")
                    break
        else:
            # audio is a 2-channel interleaved 8-bit PCMU audio stream
            # which is separated into single streams
            # using numpy
            # stream the audio to pub/sub
            array = np.frombuffer(data, dtype=np.int8)
            reshaped = array.reshape(
                (int(len(array) / 2), 2))
            # append audio to customer audio buffer
            customer_stream.fill_buffer(reshaped[:, 0].tobytes())
            # append audio to agent audio buffer
            agent_stream.fill_buffer(reshaped[:, 1].tobytes())
