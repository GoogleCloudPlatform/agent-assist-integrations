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

"""Module for managing Dialogflow conversations."""

import logging


from google.api_core import exceptions
from google.cloud import dialogflow_v2beta1 as dialogflow

# Initialize clients at module level to reuse gRPC channels across requests
# This reduces latency and prevents socket exhaustion in Cloud Run
conv_client = None


def _get_conv_client():
    global conv_client
    if conv_client is None:
        conv_client = dialogflow.ConversationsAsyncClient()
    return conv_client


profile_client = dialogflow.ConversationProfilesClient()


async def create_conversation(project_id, conversation_profile_id, conversation_id):
    """Creates a conversation with given values

    Args:
        project_id:  The GCP project linked with the conversation.
        conversation_profile_id: The conversation profile id used to create
        conversation.
        conversation_id: The custom ID for the conversation (must follow regex)."""

    project_path = f"projects/{project_id}"
    profile_path = profile_client.conversation_profile_path(
        project_id, conversation_profile_id
    )

    conversation = {"conversation_profile": profile_path}

    try:
        request = dialogflow.CreateConversationRequest(
            parent=project_path,
            conversation=conversation,
            conversation_id=conversation_id,
        )

        response = await _get_conv_client().create_conversation(request=request)
        logging.info(
            "Conversation Created: %s (State: %s)",
            response.name,
            response.lifecycle_state.name,
        )
        return response

    except exceptions.AlreadyExists:
        return await get_conversation(project_id, conversation_id)

    except exceptions.InvalidArgument as e:
        logging.debug("Invalid ID format for %s. Check regex: %s", conversation_id, e)
        raise

    except Exception as e:
        logging.debug("Failed to create conversation: %s", e)
        raise


async def get_conversation(project_id, conversation_id):
    """Gets a specific conversation profile.

    Args:
        project_id: The GCP project linked with the conversation.
        conversation_id: Id of the conversation."""

    conversation_path = _get_conv_client().conversation_path(
        project_id, conversation_id
    )

    try:
        response = await _get_conv_client().get_conversation(name=conversation_path)
        logging.debug(
            "Conversation Retrieved: %s (State: %s)",
            response.name,
            response.lifecycle_state.name,
        )

        return response
    except exceptions.NotFound:
        return None


async def complete_conversation(project_id, conversation_id):
    """
    Completes the specified conversation. Finished conversations
    are purged from the database after 30 days.

    Args:
        project_id: The GCP project linked with the conversation.
        conversation_id: Id of the conversation."""

    conversation_path = _get_conv_client().conversation_path(
        project_id, conversation_id
    )

    try:
        conversation = await _get_conv_client().complete_conversation(
            name=conversation_path
        )
        logging.debug(
            "[%s] Conversation complete: %s", conversation_id, conversation.name
        )
        return conversation
    except exceptions.NotFound:
        logging.debug(
            "[%s] Could not complete: Conversation not found.", conversation_id
        )

        return None
    except Exception as e:
        logging.debug("[%s] Error completing conversation: %s", conversation_id, e)

        return None
