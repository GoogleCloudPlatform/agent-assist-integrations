# Copyright 2022 Google LLC
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

import logging

from google.cloud import dialogflow_v2beta1 as dialogflow
from google.auth.transport.requests import AuthorizedSession
import google.auth

ROLES = ['HUMAN_AGENT', 'AUTOMATED_AGENT', 'END_USER']
LANGUAGE_CODE = 'en-US'

# static variables for dialogflow client
CONVERSATIONS_CLIENT = dialogflow.ConversationsClient()
PARTICIPANTS_CLIENT = dialogflow.ParticipantsClient()
CREDENTIALS, PROJECT_ID = google.auth.default(
    scopes=['https://www.googleapis.com/auth/dialogflow'])
AUTHED_SESSION = AuthorizedSession(CREDENTIALS)


def get_target_url(location, path):
    if location == 'global':
        return 'https://dialogflow.googleapis.com/{}'.format(path)
    return 'https://{0}-dialogflow.googleapis.com/{1}'.format(location, path)


def get_dialogflow(location, path):
    url = get_target_url(location, path)
    logging.debug('get_dialogflow {0}'.format(url))
    response = AUTHED_SESSION.get(url, stream=True)
    return response


def post_dialogflow(location, path, data=None):
    url = get_target_url(location, path)
    logging.debug('post_dialogflow {0}'.format(url))
    response = AUTHED_SESSION.post(url, json=data, stream=True)
    return response


def patch_dialogflow(location, path, data):
    url = get_target_url(location, path)
    logging.debug('patch_dialogflow {0}'.format(url))
    response = AUTHED_SESSION.patch(url, json=data, stream=True)
    return response
