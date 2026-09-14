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
"""UI connector backend service managing WebSocket and REST connections."""

from datetime import datetime
import gzip
import hashlib
import json
import logging
import os
import random
import re
import time
from typing import Any, NotRequired, TypedDict

from flask import Flask, jsonify, make_response, render_template, request
from flask_cors import CORS
from flask_socketio import join_room, leave_room, rooms, SocketIO
import redis
from socketio.exceptions import ConnectionRefusedError as SocketConnectionRefusedError

from auth import check_app_auth, check_auth, check_jwt, generate_jwt, load_jwt_secret_key, token_required
import config
import dialogflow
import webchannel

app = Flask(__name__)
CORS(app, origins=config.CORS_ALLOWED_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=config.CORS_ALLOWED_ORIGINS)
load_jwt_secret_key()

LOCATION_REGEX = re.compile(r"projects/[^/]+/locations/([^/]+)")

STREAMING_METHODS = {
    "streaming_reactive_companion_suggestions": {
        "channel_path": ("google.cloud.dialogflow.v2beta1.Participants/"
                         "StreamingReactiveCompanionSuggestions/channel"),
        "parent_field": "participant",
    }
}

ACTIVE_STREAMS = {}
SOCKET_SESSION_IDS_TO_STREAMS = {}


def redis_pubsub_handler(message):
    """Handles messages from Redis Pub/Sub."""
    logging.info("Redis Pub/Sub Received data: %s", message)
    msg_object = json.loads(message["data"])
    socketio.emit(
        msg_object["data_type"],
        msg_object,
        to=msg_object["conversation_name"],
    )
    logging.info(
        "Redis Subscribe: %s,%s,%s,%s; conversation_name: %s, data_type: %s.",
        message["type"],
        message["pattern"],
        message["channel"],
        message["data"],
        msg_object["conversation_name"],
        msg_object["data_type"],
    )


def psubscribe_exception_handler(ex, pubsub, unused_thread):  # pylint: disable=unused-argument
    """Handles exceptions in Redis pubsub listener thread."""
    logging.exception("An error occurred while getting pubsub messages: %s", ex)
    time.sleep(2)


SERVER_ID = f"{random.uniform(0, 322321)}-{datetime.now().timestamp()}"
logging.info("--------- SERVER_ID: %s ---------", SERVER_ID)
redis_client = redis.StrictRedis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    health_check_interval=10,
    socket_connect_timeout=15,
    retry_on_timeout=True,
    socket_keepalive=True,
    retry=redis.retry.Retry(redis.backoff.ExponentialBackoff(cap=5, base=1), 5),
    retry_on_error=[
        redis.exceptions.ConnectionError,
        redis.exceptions.TimeoutError,
        redis.exceptions.ResponseError,
    ],
)
p = redis_client.pubsub(ignore_subscribe_messages=True)
p.psubscribe(**{f"{SERVER_ID}:*": redis_pubsub_handler})
thread = p.run_in_thread(sleep_time=0.001,
                         exception_handler=psubscribe_exception_handler)


def get_conversation_name_without_location(conversation_name):
    """Returns a conversation name without its location id."""
    conversation_name_without_location = conversation_name
    if "/locations/" in conversation_name:
        name_array = conversation_name.split("/")
        conversation_name_without_location = "/".join(
            name_array[i] for i in [0, 1, -2, -1])
    return conversation_name_without_location


@app.route("/")
def test():
    """Shows a test page for conversation runtime handling."""
    return render_template("index.html")


@app.route("/status")
def check_status():
    """Tests whether the service is available for a domain."""
    return "Hello, cross-origin-world!"


@app.route("/register", methods=["POST"])
def register_token():
    """Registers a JWT token after checking authorization header."""
    auth = request.headers.get("Authorization", "")
    if not check_auth(auth):
        return make_response(
            "Could not authenticate user",
            401,
            {"Authentication": "valid token required"},
        )
    token = generate_jwt(request.get_json(force=True, silent=True))
    return jsonify({"token": token})


@app.route("/register-app", methods=["POST"])
def register_app_token():
    """Registers a JWT token after checking application-level auth."""
    data = request.get_json()
    if not check_app_auth(data):
        return make_response(
            "Could not authenticate user",
            401,
            {"Authentication": "valid application level auth required"},
        )
    token = generate_jwt(request.get_json(force=True, silent=True))
    return jsonify({"token": token})


def call_dialogflow(version, project, location, tail):  # pylint: disable=unused-argument
    """Forwards valid request to dialogflow and return its response."""
    logging.info("Called Dialogflow for request path: %s", request.full_path)
    if request.method == "GET":
        response = dialogflow.get_dialogflow(location, request.full_path)
        logging.info(
            "get_dialogflow response: %s, %s, %s",
            gzip.decompress(response.raw.data),
            response.status_code,
            response.headers,
        )
        return response.raw.data, response.status_code, response.headers.items()
    if request.method == "POST":
        # Handles projects.conversations.complete with empty request body.
        if request.path.endswith(":complete"):
            response = dialogflow.post_dialogflow(location, request.full_path)
        else:
            response = dialogflow.post_dialogflow(location, request.full_path,
                                                  request.get_json())
        logging.info(
            "post_dialogflow response: %s, %s, %s",
            response.raw.data,
            response.status_code,
            response.headers,
        )
        return response.raw.data, response.status_code, response.headers.items()
    response = dialogflow.patch_dialogflow(location, request.full_path,
                                           request.get_json())
    logging.info(
        "patch_dialogflow response: %s, %s, %s",
        response.raw.data,
        response.status_code,
        response.headers,
    )
    return response.raw.data, response.status_code, response.headers.items()


# projects.locations.conversations.create
@app.route(
    "/<version>/projects/<project>/locations/<location>/conversations",
    methods=["POST"],
)
# projects.locations.suggestions.searchKnowledge
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "suggestions:searchKnowledge",
    methods=["POST"],
)
# projects.locations.conversations.generateStatelessSuggestion
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "statelessSuggestion:generate",
    methods=["POST"],
)
@token_required
def call_dialogflow_without_tail(version, project, location):
    """Handles Dialogflow calls that do not have a sub-path tail."""
    return call_dialogflow(version, project, location, "")


# Note: Dialogflow methods projects.locations.conversations.list and
# projects.locations.answerRecords.list are not supported.


# projects.locations.answerRecords.patch
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "answerRecords/<path:tail>",
    methods=["PATCH"],
)
# projects.locations.conversations.participants.patch
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "conversations/<path:tail>",
    methods=["PATCH"],
)
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
#   ...participants.suggestions.suggestSmartReplies
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "conversations/<path:tail>",
    methods=["GET", "POST"],
)
# projects.locations.conversationProfiles.get
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "conversationProfiles/<path:tail>",
    methods=["GET"],
)
# projects.locations.conversationModels.get
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "conversationModels/<path:tail>",
    methods=["GET"],
)
# projects.locations.generators.get
@app.route(
    "/<version>/projects/<project>/locations/<location>/"
    "generators/<path:tail>",
    methods=["GET"],
)
@token_required
def call_dialogflow_with_tail(version, project, location, tail):
    """Handles Dialogflow calls that contain a sub-path tail."""
    return call_dialogflow(version, project, location, tail)


@app.route("/conversation-name", methods=["POST"])
@token_required
def set_conversation_name():
    """Sets a conversationIntegrationKey:conversationName pair in Redis."""
    conversation_integration_key = request.json.get(
        "conversationIntegrationKey", "")
    hashed_key = hashlib.sha256(
        conversation_integration_key.encode("utf-8")).hexdigest()
    conversation_name = request.json.get("conversationName", "")
    logging.info(
        "/conversation-name - redis: SET %s %s",
        conversation_integration_key,
        conversation_name,
    )
    result = redis_client.set(hashed_key, conversation_name)
    if not (conversation_integration_key and conversation_name and result):
        return make_response("Bad request", 400)
    return jsonify({conversation_integration_key: conversation_name})


@app.route("/conversation-name", methods=["GET"])
@token_required
def get_conversation_name():
    """Gets a DialogFlow conversation name from Redis."""
    conversation_integration_key = str(
        request.args.get("conversationIntegrationKey"))
    hashed_key = hashlib.sha256(
        conversation_integration_key.encode("utf-8")).hexdigest()
    conversation_name = redis_client.get(hashed_key)
    logging.info(
        "/conversation-name - redis: GET %s -> %s",
        conversation_integration_key,
        conversation_name,
    )
    if not conversation_integration_key:
        return make_response("Bad request", 400)
    return jsonify({
        "conversationName": (str(conversation_name, encoding="utf-8")
                             if conversation_name else "")
    })


@app.route("/conversation-name", methods=["DELETE"])
@token_required
def del_conversation_name():
    """Deletes a DialogFlow conversation name from Redis."""
    conversation_integration_key = str(
        request.args.get("conversationIntegrationKey"))
    hashed_key = hashlib.sha256(
        conversation_integration_key.encode("utf-8")).hexdigest()
    result = redis_client.delete(hashed_key)
    logging.info(
        "/conversation-name - redis: DEL %s, result %s",
        conversation_integration_key,
        result,
    )
    if conversation_integration_key == "None":
        return make_response("Bad request", 400)
    if not result:
        return make_response("Not found", 404)
    return make_response("Success", 200)


@socketio.on("connect")
def connect(auth=None):
    """Handles SocketIO client connection and authentication."""
    if auth is None:
        auth = {}
    logging.info("Receives connection request with sid: %s.", request.sid)
    if isinstance(auth, dict) and "token" in auth:
        is_valid, log_info = check_jwt(auth["token"])
        logging.info(log_info)
        if is_valid:
            return True
    socketio.emit("unauthenticated")
    raise SocketConnectionRefusedError("authentication failed")


@socketio.on("disconnect")
def disconnect(reason):
    """Handles SocketIO client disconnection."""
    logging.info("Client disconnected, reason: %s, request.sid: %s", reason,
                 request.sid)
    stream_ids = SOCKET_SESSION_IDS_TO_STREAMS.pop(request.sid, set())
    for stream_id in stream_ids:
        client = ACTIVE_STREAMS.pop(stream_id, None)
        if client:
            client.close(reason=f"socket_disconnect: {reason}")
    room_list = rooms()
    # Delete mapping for conversation_name and SERVER_ID.
    if len(room_list) > 1:
        room_list.pop(0)  # the first one in room list is request.sid
        redis_client.delete(*room_list)


@app.errorhandler(500)
def server_error(e):
    """Handles Flask HTTP errors."""
    logging.exception("An error occurred during a request.")
    return (
        f"An internal error occurred: <pre>{e}</pre>\n"
        "See logs for full stacktrace.\n",
        500,
    )


@socketio.on("join-conversation")
def on_join(message):
    """Joins a room specified by its conversation name."""
    logging.info("Received event: join-conversation: %s", message)
    # Remove location id from the conversation name.
    conversation_name = get_conversation_name_without_location(message)
    join_room(conversation_name)
    # Update mapping for conversation_name and SERVER_ID.
    redis_client.set(conversation_name, SERVER_ID)
    logging.info("join-conversation for: %s", conversation_name)
    return True, conversation_name


@socketio.on("leave-conversation")
def on_leave(message):
    """Leaves a room specified by its conversation name."""
    logging.info("Received event: leave-conversation: %s", message)
    # Remove location id from the conversation name.
    conversation_name = get_conversation_name_without_location(message)
    leave_room(conversation_name)
    # Delete mapping for conversation_name and SERVER_ID.
    redis_client.delete(conversation_name)
    logging.info("leave-conversation for: %s", conversation_name)
    return True, conversation_name


def _emit_stream_error(sid: str, stream_id: str, err_msg: str):
    """Emits a structured Dialogflow API error to the target client."""
    socketio.emit(
        "stream-error",
        {
            "streamId": stream_id,
            "payload": {
                "error": {
                    "message": err_msg,
                    "code": 13,
                }
            },
        },
        to=sid,
    )


def _emit_stream_data(sid: str, stream_id: str, payload: dict[str, Any]):
    """Emits deserialized WebChannel chunk data to the target client."""
    socketio.emit(
        "stream-data",
        {
            "streamId": stream_id,
            "payload": payload
        },
        to=sid,
    )


def _cleanup_stream(sid: str, stream_id: str):
    """Unregisters stream from active tracking maps."""
    ACTIVE_STREAMS.pop(stream_id, None)
    client_streams = SOCKET_SESSION_IDS_TO_STREAMS.get(sid)
    if client_streams and stream_id in client_streams:
        client_streams.discard(stream_id)


class StreamRequestData(TypedDict):
    # pylint: disable=invalid-name
    streamId: str
    method: str
    payload: NotRequired[dict[str, Any]]


@socketio.on("stream-request")
def handle_stream_request(data: StreamRequestData):
    """Handles a streaming RPC proxy request over WebChannel."""
    stream_id = data.get("streamId")
    if not stream_id:
        return

    payload = data.get("payload")

    if stream_id in ACTIVE_STREAMS:
        if payload is not None:
            ACTIVE_STREAMS[stream_id].send(payload)
        return

    method_name = data.get("method")
    if not method_name:
        _emit_stream_error(
            request.sid,
            stream_id,
            'Missing required "method" parameter in initial stream-request.',
        )
        return

    method_config = STREAMING_METHODS.get(method_name)
    if not method_config:
        _emit_stream_error(
            request.sid,
            stream_id,
            f"Unknown streaming method: {method_name}",
        )
        return

    parent_field = method_config.get("parent_field", "")
    parent_value = ""
    if isinstance(payload, dict) and parent_field:
        parent_value = payload.get(parent_field, "")

    match = LOCATION_REGEX.search(parent_value)
    if not match:
        _emit_stream_error(
            request.sid,
            stream_id,
            f"Could not extract location from {parent_field}: "
            f'"{parent_value}".',
        )
        return

    location = match.group(1)
    endpoint_url = webchannel.get_streaming_rpc_url(
        method_config["channel_path"], location)

    web_channel = webchannel.WebChannelClient(endpoint_url)

    sid = request.sid

    web_channel.onResponse(
        lambda res_payload: _emit_stream_data(sid, stream_id, res_payload))
    web_channel.onError(
        lambda err_msg: _emit_stream_error(sid, stream_id, err_msg))
    web_channel.onClose(lambda: _cleanup_stream(sid, stream_id))

    ACTIVE_STREAMS[stream_id] = web_channel
    SOCKET_SESSION_IDS_TO_STREAMS.setdefault(sid, set()).add(stream_id)

    logging.info(
        "stream-request received for %s with method %s",
        stream_id,
        method_name,
    )
    web_channel.connect()

    if payload is not None:
        web_channel.send(payload)


@socketio.on("end-stream")
def handle_end_stream(data):
    """Terminates active WebChannel stream and releases client resources."""
    stream_id = data.get("streamId")
    if stream_id in ACTIVE_STREAMS:
        ACTIVE_STREAMS[stream_id].close(reason="client_end_stream_event")
    _cleanup_stream(request.sid, stream_id)


@socketio.on_error_default
def default_error_handler(e):
    """Handles SocketIO event errors."""
    logging.exception("error from %s event: %s", request.event["message"], e)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="127.0.0.1", port=port, debug=True)
