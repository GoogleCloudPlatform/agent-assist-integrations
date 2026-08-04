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

"""Module for Audiohook protocol message exchange
"""
import logging

DEFAULT_CONVERSATION_ID = "00000000-0000-0000-0000-000000000000"
AUDIOHOOK_VERSION = "2"


class AudioHook:
    """Audiohook protocol implementation
    Reference: https://developer.genesys.cloud/devapps/audiohook/session-walkthrough#establishing-connection

    `
     The server and client each maintain a monotonically increasing message sequence number to determine the which message
     the party has already seen and which is still in flight
    `
    Returns:
        _type_: Audiohook type definition based on the protocol definition
    """

    def __init__(self):
        self.pre_server_sequence = 0
        self.pre_client_sequence = 0
        self.server_sequence = 0
        self.client_sequence = 0
        self.session_id = 0
        self.first_resume = True

    def create_opened_message(self):
        """On receiving the "open" message, the server
        picks the audio format and respond with an "opened" message
        """
        opened_message = self.create_message_by_type(
            message_type="opened")
        opened_message["parameters"] = {
            "startPaused": True,
            "media": [
                {
                    "type": "audio",
                    "format": "PCMU",
                    "channels": ["external", "internal"],
                    "rate": 8000,
                }
            ],
        }
        logging.debug("Get opened message %s", opened_message)

        return opened_message

    def create_resume_message(self):
        """The resume message send back to Genesys Audiohook client
        When the server is ready to process the Audio.
        """
        resume_message = self.create_message_by_type(
            message_type="resume")
        logging.debug("send resume messages to the client %s", resume_message)
        return resume_message

    def create_close_message(self):
        """The server must respond the client a "closed" message response
        to indicate the Genesys Audiohook client it is done. And the client
        then close the TLS connection
        """
        return self.create_message_by_type(
            message_type="closed")

    def create_pong_message(self):
        """Once receive a "ping" message from the Audiohook client,
        the server must respond with a "pong" message to keep the connection alive
        """
        pong_message = self.create_message_by_type(
            message_type="pong")
        logging.debug("send pong messages to the client %s", pong_message)
        return pong_message

    def set_session_id(self, session_id: str):
        """Set function for session id

        Args:
            session_id (str): Unique identifier of the streaming session as a UUID string
        """
        self.session_id = session_id

    def set_client_sequence(self, client_sequence):
        """Keep the sequence from Audio connector

        Args:
            client_sequence (int): _description_
        """
        self.client_sequence = client_sequence

    def create_message_by_type(
        self,
        message_type: str,
    ):
        """Create standard message format required by the Audiohook protocol
        """
        self.pre_server_sequence = self.server_sequence
        self.server_sequence += 1
        return {
            "version": AUDIOHOOK_VERSION,
            "type": message_type,
            "seq": self.server_sequence,
            "clientseq": self.client_sequence,
            "id": self.session_id,
            "parameters": {},
        }
