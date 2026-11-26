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
import ssl
import json
from datetime import datetime

from flask import Flask, request

# Cloud run could recognize logging files under '/var/log/' folder
# Can be overridden via LOGGING_FILE for local testing
logging.basicConfig(filename=os.environ.get('LOGGING_FILE', '/var/log/test.log'), level=logging.INFO)
app = Flask(__name__)


def get_redis_tls_kwargs(tls_enabled, ca_cert_path, ca_cert_pem):
    """Returns TLS kwargs for redis.StrictRedis when REDIS_TLS_ENABLED=true.

    Progressive upgrade: returns an empty dict when TLS is disabled.
    When enabled, enforces TLS 1.2+ with required Server CA verification and
    fails closed if no CA certificate file or PEM string is provided.
    """
    if not tls_enabled:
        return {}
    tls_kwargs = {
        'ssl': True,
        'ssl_cert_reqs': 'required',
        'ssl_min_version': ssl.TLSVersion.TLSv1_2,
    }
    if ca_cert_path and os.path.isfile(ca_cert_path):
        tls_kwargs['ssl_ca_certs'] = ca_cert_path
    elif ca_cert_pem:
        tls_kwargs['ssl_ca_data'] = ca_cert_pem.replace('\\n', '\n')
    else:
        raise ValueError(
            'REDIS_TLS_ENABLED is true, but no Memorystore Server CA '
            'certificate was found. Mount the CA PEM at REDIS_CA_CERT_PATH '
            'or set REDIS_CA_CERT_PEM.'
        )
    return tls_kwargs


# Redis setup
redis_host = os.environ.get('REDISHOST', 'localhost')
redis_port = int(os.environ.get('REDISPORT', 6379))
redis_tls_enabled = os.environ.get('REDIS_TLS_ENABLED', '').strip().lower() in (
    'true',
    '1',
    'yes',
)
redis_ca_cert_path = os.environ.get(
    'REDIS_CA_CERT_PATH', '/secret/redis_ca_cert.pem'
)
redis_ca_cert_pem = os.environ.get('REDIS_CA_CERT_PEM', '')
redis_client = redis.StrictRedis(
    host=redis_host, port=redis_port,
    health_check_interval=10,
    socket_connect_timeout=15,
    retry_on_timeout=True,
    socket_keepalive=True,
    retry=redis.retry.Retry(redis.backoff.ExponentialBackoff(cap=5, base=1), 5),
    retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, redis.exceptions.ResponseError],
    **get_redis_tls_kwargs(
        redis_tls_enabled,
        redis_ca_cert_path,
        redis_ca_cert_pem,
    ))


def get_conversation_name_without_location(conversation_name):
    """Returns a conversation name without its location id."""
    conversation_name_without_location = conversation_name
    if '/locations/' in conversation_name:
        name_array = conversation_name.split('/')
        conversation_name_without_location = '/'.join(
            name_array[i] for i in [0, 1, -2, -1])
    return conversation_name_without_location


def get_conversation_servers_key(conversation_name):
    """Returns the Redis key of the set of instances serving a conversation.

    Must match get_conversation_servers_key in the UI Connector service.
    """
    return f'{conversation_name}:servers'


_WARNING_LOG_FMT = 'Warning: %s'


def _extract_pubsub_message(envelope):
    """Validates the Cloud Pub/Sub HTTP envelope and returns its message dict."""
    if not envelope:
        logging.warning(_WARNING_LOG_FMT, 'No Pub/Sub message received.')
        return None
    if not isinstance(envelope, dict) or 'message' not in envelope:
        logging.warning(_WARNING_LOG_FMT, 'Invalid Pub/Sub message format.')
        return None
    pubsub_message = envelope['message']
    if not isinstance(pubsub_message, dict):
        logging.warning(
            _WARNING_LOG_FMT,
            'Invalid Pub/Sub message, message inside the envelope should be '
            'valid JSON format https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage.',
        )
        return None
    return pubsub_message


def _extract_recognition_attributes(pubsub_message):
    """Extracts participant_role and message_id from Pub/Sub message attributes."""
    attributes = pubsub_message.get('attributes')
    if not isinstance(attributes, dict):
        return '', ''
    return attributes.get('participant_role', ''), attributes.get('message_id', '')


def _publish_conversation_event(
    conversation_name,
    data,
    data_type,
    pubsub_message,
    participant_role,
    new_recognition_result_message_id,
):
    """Builds the Redis payload and fans it out to all serving UI Connectors."""
    msg_data = {
        'conversation_name': conversation_name,
        'data': data,
        'data_type': data_type,
        # The timestamp when the server receives this message.
        # It could help with analyzing service time of each part of the backend
        # infrastructure, which can be used for load testing.
        'ack_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'publish_time': pubsub_message.get('publishTime', ''),
        'message_id': pubsub_message.get('messageId', ''),
    }
    if data_type == 'new-recognition-result-notification-event':
        msg_data['participant_role'] = participant_role
        msg_data['new_recognition_result_message_id'] = new_recognition_result_message_id
        logging.debug(
            'participant role %s message id %s for new recognition result',
            participant_role,
            new_recognition_result_message_id,
        )

    server_ids = redis_client.smembers(
        get_conversation_servers_key(conversation_name)
    )
    if not server_ids:
        logging.warning(
            'No SERVER_ID (UI Connector instance) for conversation name %s. '
            'Please subscribe to the conversation by sending join-conversation event.',
            conversation_name,
        )
        return

    # Multiple UI Connector instances can serve one conversation (e.g.
    # agents on different instances during a transfer); publish to each.
    msg_json = json.dumps(msg_data)
    for server_id in server_ids:
        server = server_id.decode('utf-8')
        channel = '{}:{}'.format(server, conversation_name)
        redis_client.publish(channel, msg_json)
        logging.debug(
            'Redis publish (message_id: %s, publish_time: %s, conversation_name: %s, channel: %s, data_type: %s.',
            pubsub_message.get('messageId', ''),
            pubsub_message.get('publishTime', ''),
            conversation_name,
            channel,
            data_type,
        )


def cloud_pubsub_handler(request, data_type):
    """Verifies and forwards requests from Cloud Pub/Sub to Redis."""
    pubsub_message = _extract_pubsub_message(request.get_json(silent=True))
    if pubsub_message is None:
        return

    participant_role, new_recognition_result_message_id = (
        _extract_recognition_attributes(pubsub_message)
    )
    if 'data' not in pubsub_message:
        return

    try:
        data = base64.b64decode(pubsub_message['data']).decode('utf-8')
        logging.debug('Subscribed Pub/Sub message: %s', data)
        data_object = json.loads(data)
    except ValueError as e:
        logging.warning(
            _WARNING_LOG_FMT,
            f'Failed to decode/parse Pub/Sub message data: {e}',
        )
        return
    if not isinstance(data_object, dict) or 'conversation' not in data_object:
        logging.warning(
            _WARNING_LOG_FMT,
            'Cannot extract conversation id from Pub/Sub request.',
        )
        return

    conversation_name = get_conversation_name_without_location(
        data_object['conversation']
    )
    logging.debug(
        'conversation_name: %s, conversation_name_without_location: %s',
        data_object['conversation'],
        conversation_name,
    )
    _publish_conversation_event(
        conversation_name,
        data,
        data_type,
        pubsub_message,
        participant_role,
        new_recognition_result_message_id,
    )


@app.route('/human-agent-assistant-event', methods=['POST'])
def subscribe_suggestions():
    """Receives new human agent assist events from pre-configured dialogflow Pub/Sub topic."""
    cloud_pubsub_handler(request, 'human-agent-assistant-event')
    return ('Received by cloud run service as a HumanAgentAssistantEvent.', 204)


@app.route('/conversation-lifecycle-event', methods=['POST'])
def subscribe_lifecycle_events():
    """Receives new conversation events from pre-configured dialogflow Pub/Sub topic."""
    cloud_pubsub_handler(request, 'conversation-lifecycle-event')
    return ('Received by cloud run service as a ConversationEvent.', 204)


@app.route('/new-message-event', methods=['POST'])
def subscribe_message_events():
    """Receives new message events from pre-configured dialogflow Pub/Sub topic."""
    cloud_pubsub_handler(request, 'new-message-event')
    return ('Received by cloud run service as a ConversationEvent.', 204)


@app.route('/new-recognition-result-notification-event', methods=['POST'])
def subscribe_new_recognition_result_events():
    """Receives new recognition result events from pre-configured dialogflow Pub/Sub topic."""
    cloud_pubsub_handler(request, 'new-recognition-result-notification-event')
    return ('Received by cloud run service as a New recognition result notification.', 204)


if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)
