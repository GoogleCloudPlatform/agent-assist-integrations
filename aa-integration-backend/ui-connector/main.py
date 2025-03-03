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
import os
import json
import random
from datetime import datetime

from flask import Flask, request, make_response, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from socketio.exceptions import ConnectionRefusedError
import redis

import config
import dialogflow
from auth import check_auth, generate_jwt, token_required, check_jwt, load_jwt_secret_key

app = Flask(__name__)
CORS(app, origins=config.CORS_ALLOWED_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=config.CORS_ALLOWED_ORIGINS)
load_jwt_secret_key()


def redis_pubsub_handler(message):
    """Handles messages from Redis Pub/Sub."""
    logging.info('Redis Pub/Sub Received data: {}'.format(message))
    msg_object = json.loads(message['data'])
    socketio.emit(msg_object['data_type'], msg_object,
                  to=msg_object['conversation_name'])
    logging.info('Redis Subscribe: {0},{1},{2},{3}; conversation_name: {4}, data_type: {5}.'.format(
        message['type'],
        message['pattern'],
        message['channel'],
        message['data'],
        msg_object['conversation_name'],
        msg_object['data_type']))


SERVER_ID = '{}-{}'.format(random.uniform(0, 322321),
                           datetime.now().timestamp())
logging.info('--------- SERVER_ID: {} ---------'.format(SERVER_ID))
redis_client = redis.StrictRedis(
    host=config.REDIS_HOST, port=config.REDIS_PORT)
p = redis_client.pubsub(ignore_subscribe_messages=True)
p.psubscribe(**{'{}:*'.format(SERVER_ID): redis_pubsub_handler})
thread = p.run_in_thread()

def get_conversation_name_without_location(conversation_name):
    """Returns a conversation name without its location id."""
    conversation_name_without_location = conversation_name
    if '/locations/' in conversation_name:
        name_array = conversation_name.split('/')
        conversation_name_without_location = '/'.join(
            name_array[i] for i in [0, 1, -2, -1])
    return conversation_name_without_location

@app.route('/')
def test():
    """Shows a test page for conversation runtime handling.
    """
    return render_template('index.html')


@app.route('/status')
def check_status():
    """Tests whether the service is available for a domain.
       Remove this function if it's not necessary for you.
    """
    return 'Hello, cross-origin-world!'


@app.route('/register', methods=['POST'])
def register_token():
    """Registers a JWT token after checking authorization header."""
    auth = request.headers.get('Authorization')
    if not check_auth(auth):
        return make_response('Could not authenticate user', 401, {'Authentication': 'valid token required'})
    token = generate_jwt(request.get_json(force=True, silent=True))
    return jsonify({'token': token})

# Note: Dialogflow methods projects.locations.conversations.list and projects.locations.answerRecords.list are not supported.


# projects.locations.answerRecords.patch
@app.route('/<version>/projects/<project>/locations/<location>/answerRecords/<path:path>', methods=['PATCH'])
# projects.locations.conversations.participants.patch
@app.route('/<version>/projects/<project>/locations/<location>/conversations/<path:path>', methods=['PATCH'])
# projects.locations.conversations.create
@app.route('/<version>/projects/<project>/locations/<location>/conversations', defaults={'path': ''}, methods=['POST'])
# GET:
#   projects.locations.conversations.get
#   projects.locations.conversations.messages.list
#   projects.locations.conversations.participants.get
#   projects.locations.conversations.participants.list
# POST:
#   projects.locations.conversations.complete
#   projects.locations.conversations.create
#   projects.locations.conversations.messages.batchCreate
#   projects.locations.conversations.participants.analyzeContent
#   projects.locations.conversations.participants.create
#   projects.locations.conversations.participants.suggestions.suggestArticles
#   projects.locations.conversations.participants.suggestions.suggestFaqAnswers
#   projects.locations.conversations.participants.suggestions.suggestSmartReplies
@app.route('/<version>/projects/<project>/locations/<location>/conversations/<path:path>', methods=['GET', 'POST'])
# projects.locations.conversationProfiles.get
@app.route('/<version>/projects/<project>/locations/<location>/conversationProfiles/<path:path>', methods=['GET'])
# projects.locations.conversationModels.get
@app.route('/<version>/projects/<project>/locations/<location>/conversationModels/<path:path>', methods=['GET'])
# projects.locations.suggestions.searchKnowledge
@app.route('/<version>/projects/<project>/locations/<location>/suggestions:searchKnowledge', defaults={'path': None}, methods=['POST'])
# projects.locations.conversations.generateStatelessSuggestion
@app.route('/<version>/projects/<project>/locations/<location>/statelessSuggestion:generate', defaults={'path': None}, methods=['POST'])
# projects.locations.generators.get
@app.route('/<version>/projects/<project>/locations/<location>/generators/<path:path>', methods=['GET'])
@token_required
def call_dialogflow(version, project, location, path):
    """Forwards valid request to dialogflow and return its responese."""
    logging.info(
        'Called Dialogflow for request path: {}'.format(request.full_path))
    if request.method == 'GET':
        response = dialogflow.get_dialogflow(location, request.full_path)
        logging.info('get_dialogflow response: {0}, {1}, {2}'.format(
            response.raw.data, response.status_code, response.headers))
        return response.raw.data, response.status_code, response.headers.items()
    elif request.method == 'POST':
        # Handles projects.conversations.complete, whose request body should be empty.
        response = None
        if request.path.endswith(':complete'):
            response = dialogflow.post_dialogflow(location, request.full_path)
        else:
            response = dialogflow.post_dialogflow(
                location, request.full_path, request.get_json())
        logging.info('post_dialogflow response: {0}, {1}, {2}'.format(
            response.raw.data, response.status_code, response.headers))
        return response.raw.data, response.status_code, response.headers.items()
    else:
        response = dialogflow.patch_dialogflow(
            location, request.full_path, request.get_json())
        logging.info('patch_dialogflow response: {0}, {1}, {2}'.format(
            response.raw.data, response.status_code, response.headers))
        return response.raw.data, response.status_code, response.headers.items()


@socketio.on('connect')
def connect(auth):
    logging.info(
        'Receives connection request with sid: {0}.'.format(request.sid))
    if 'token' in auth:
        is_valid, log_info = check_jwt(auth['token'])
        logging.info(log_info)
        if is_valid:
            return True
    socketio.emit('unauthenticated')
    raise ConnectionRefusedError('authentication failed')


@socketio.on('disconnect')
def disconnect(reason):
    logging.info('Client disconnected, reason: {}, request.sid: {}'.format(reason, request.sid))
    room_list = rooms()
    # Delete mapping for conversation_name and SERVER_ID.
    if len(room_list) > 1:
        room_list.pop(0)  # the first one in room list is request.sid
        redis_client.delete(*room_list)


@app.errorhandler(500)
def server_error(e):
    """Handles Flask HTTP errors."""
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


@socketio.on('join-conversation')
def on_join(message):
    """Joins a room specified by its conversation name."""
    logging.info('Received event: join-conversation: {}'.format(message))
    # Remove location id from the conversation name.
    conversation_name = get_conversation_name_without_location(message)
    join_room(conversation_name)
    # Update mapping for conversation_name and SERVER_ID.
    redis_client.set(conversation_name, SERVER_ID)
    logging.info(
            'join-conversation for: {}'.format(conversation_name))
    return True, conversation_name


@socketio.on('leave-conversation')
def on_leave(message):
    """Leaves a room specified by its conversation name."""
    logging.info('Received event: leave-conversation: {}'.format(message))
    # Remove location id from the conversation name.
    conversation_name = get_conversation_name_without_location(message)
    leave_room(conversation_name)
    # Delete mapping for conversation_name and SERVER_ID.
    redis_client.delete(conversation_name)
    logging.info(
            'leave-conversation for: {}'.format(conversation_name))
    return True, conversation_name

@socketio.on_error_default
def default_error_handler(e):
    """Handles SocketIO event errors."""
    logging.exception('error from {0} event: {1}'.format(
        request.event['message'], e))


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the application
    # on Google App Engine and Cloud Run. See entrypoint in Dockerfile.
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='127.0.0.1', port=port, debug=True)
