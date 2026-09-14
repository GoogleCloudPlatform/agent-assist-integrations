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
"""Dialogflow client and session management for UI connector."""

import logging

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import dialogflow_v2beta1 as dialogflow

ROLES = ["HUMAN_AGENT", "AUTOMATED_AGENT", "END_USER"]
LANGUAGE_CODE = "en-US"

# static variables for dialogflow client
CONVERSATIONS_CLIENT = dialogflow.ConversationsClient()
PARTICIPANTS_CLIENT = dialogflow.ParticipantsClient()

try:
    CREDENTIALS, PROJECT_ID = google.auth.default(
        scopes=["https://www.googleapis.com/auth/dialogflow"])
except Exception:  # pylint: disable=broad-exception-caught
    CREDENTIALS = None
    PROJECT_ID = None

AUTHED_SESSION = AuthorizedSession(CREDENTIALS) if CREDENTIALS else None


def _get_authed_session():
    """Returns active AuthorizedSession or raises RuntimeError if None."""
    if not AUTHED_SESSION:
        raise RuntimeError(
            "No credentials available for Dialogflow AuthorizedSession.")
    return AUTHED_SESSION


def get_target_url(location, path):
    """Returns target URL for Dialogflow API requests."""
    if location == "global":
        return f"https://dialogflow.googleapis.com/{path}"
    return f"https://{location}-dialogflow.googleapis.com/{path}"


def get_dialogflow(location, path):
    """Sends GET request to Dialogflow API."""
    url = get_target_url(location, path)
    logging.debug("get_dialogflow %s", url)
    response = _get_authed_session().get(url, stream=True)
    return response


def post_dialogflow(location, path, data=None):
    """Sends POST request to Dialogflow API."""
    url = get_target_url(location, path)
    logging.debug("post_dialogflow %s", url)
    response = _get_authed_session().post(url, json=data, stream=True)
    return response


def patch_dialogflow(location, path, data):
    """Sends PATCH request to Dialogflow API."""
    url = get_target_url(location, path)
    logging.debug("patch_dialogflow %s", url)
    response = _get_authed_session().patch(url, json=data, stream=True)
    return response
