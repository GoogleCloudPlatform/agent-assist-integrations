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


from google.cloud import dialogflow_v2beta1 as dialogflow

# Initialize client once at the module level for resource efficiency in Cloud Run
conversation_profiles_client = None


def _get_conversation_profiles_client():
    global conversation_profiles_client
    if conversation_profiles_client is None:
        conversation_profiles_client = dialogflow.ConversationProfilesClient()
    return conversation_profiles_client


def get_conversation_profile(profile_name: str):
    """Gets a conversation profile by resource name.

    Args:
        profile_name: The GCP profile name."""

    return _get_conversation_profiles_client().get_conversation_profile(
        name=profile_name)
