# Copyright 2025 Google LLC
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
import base64
import os
import redis
import json
from datetime import datetime

from flask import Flask, request

# Cloud run could recognize logging files under '/var/log/' folder
# Comment this line for local test
logging.basicConfig(filename='/var/log/test.log', level=logging.INFO)
app = Flask(__name__)

# Redis setup
redis_host = os.environ.get('REDISHOST', 'localhost')
redis_port = int(os.environ.get('REDISPORT', 6379))
redis_client = redis.StrictRedis(
    host=redis_host, port=redis_port,
    health_check_interval=10,
    socket_connect_timeout=15,
    retry_on_timeout=True,
    socket_keepalive=True,
    retry=redis.retry.Retry(redis.backoff.ExponentialBackoff(cap=5, base=1), 5),
    retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, redis.exceptions.ResponseError])


def get_conversation_name_without_location(conversation_name):
    """Returns a conversation name without its location id."""
    conversation_name_without_location = conversation_name
    if '/locations/' in conversation_name:
        name_array = conversation_name.split('/')
        conversation_name_without_location = '/'.join(
            name_array[i] for i in [0, 1, -2, -1])
    return conversation_name_without_location


def cloud_pubsub_handler(request, data_type):
    """Verifies and checks requests from Cloud Pub/Sub."""
    envelope = request.get_json()
    if not envelope:
        msg = 'No Pub/Sub message received.'
        logging.warning('Warning: {}'.format(msg))
        return True

    if not isinstance(envelope, dict) or 'message' not in envelope:
        msg = 'Invalid Pub/Sub message format.'
        logging.warning('Warning: {}'.format(msg))
        return True

    pubsub_message = envelope['message']
    participant_role = ""
    new_recognition_result_message_id = ''

    if not isinstance(pubsub_message, dict):
        msg = 'Invalid Pub/Sub message, message inside the envelope should be valid JSON format https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage.'
        logging.warning('Warning: {}'.format(msg))
        return True

    if 'attributes' in pubsub_message:
        attributes = pubsub_message['attributes']
        if attributes is not None and isinstance(attributes, dict):
            if "participant_role" in attributes:
                participant_role = attributes['participant_role']
            if "message_id" in attributes:
                new_recognition_result_message_id = attributes['message_id']

    if 'data' in pubsub_message:
        data = base64.b64decode(pubsub_message['data']).decode('utf-8')
        logging.debug('Subscribed Pub/Sub message: {}'.format(data))
        data_object = json.loads(data)
        if 'conversation' not in data_object:
            msg = 'Cannot extract conversation id from Pub/Sub request.'
            logging.warning('Warning: {}'.format(msg))
            return True

        conversation_name = data_object['conversation']
        conversation_name = get_conversation_name_without_location(conversation_name)
        logging.debug('conversation_name: {0}, conversation_name_without_location: {1}'.format(data_object['conversation'], conversation_name))

        # Emits messages to redis pub/sub
        msg_data = {'conversation_name': conversation_name,
                    'data': data,
                    'data_type': data_type,
                    # The timestamp when the server receives this message.
                    # It could help with analyzing service time of each part of the backend
                    # infrastructure, which can be used for load testing.
                    'ack_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'publish_time': pubsub_message['publishTime'],
                    'message_id': pubsub_message['messageId']}
        server_id = '1'
        if data_type == 'new-recognition-result-notification-event':
            msg_data['participant_role'] = participant_role
            msg_data['new_recognition_result_message_id'] = new_recognition_result_message_id
            logging.debug('participant role {0} message id {1} for new recognition result'.format(
                participant_role, new_recognition_result_message_id))
        if redis_client.exists(conversation_name) == 0:
            logging.warning(
                "No SERVER_ID (UI Connector instance) for conversation name {}. Please subscribe to the conversation by sending join-conversation event.".format(conversation_name))
            return True
        else:
            server_id = redis_client.get(conversation_name).decode('utf-8')
        channel = '{}:{}'.format(server_id, conversation_name)
        redis_client.publish(channel, json.dumps(msg_data))
        logging.debug(
            'Redis publish (message_id: {0}, publish_time: {1}, conversation_name: {2}, channel: {3}, data_type: {4}.'.format(
                pubsub_message['messageId'], pubsub_message['publishTime'], conversation_name, channel, data_type))
    return True


@app.route('/human-agent-assistant-event', methods=['POST'])
def subscribe_suggestions():
    """Receives new human agent assist events from pre-configured dialogflow Pub/Sub topic."""
    if not cloud_pubsub_handler(request, 'human-agent-assistant-event'):
        return f'Bad Request', 400

    return ('Received by cloud run service as a HumanAgentAssistantEvent.', 204)


@app.route('/conversation-lifecycle-event', methods=['POST'])
def subscribe_lifecycle_events():
    """Receives new conversation events from pre-configured dialogflow Pub/Sub topic."""
    if not cloud_pubsub_handler(request, 'conversation-lifecycle-event'):
        return f'Bad Request', 400

    return ('Received by cloud run service as a ConversationEvent.', 204)


@app.route('/new-message-event', methods=['POST'])
def subscribe_message_events():
    """Receives new message events from pre-configured dialogflow Pub/Sub topic."""
    if not cloud_pubsub_handler(request, 'new-message-event'):
        return f'Bad Request', 400

    return ('Received by cloud run service as a ConversationEvent.', 204)


@app.route('/new-recognition-result-notification-event', methods=['POST'])
def subscribe_new_recognition_result_events():
    """Receives new recognition result events from pre-configured dialogflow Pub/Sub topic."""
    if not cloud_pubsub_handler(request, 'new-recognition-result-notification-event'):
        return f'Bad Request', 400

    return ('Received by cloud run service as a New recognition result notification.', 204)


if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)
