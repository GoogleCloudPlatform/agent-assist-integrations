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
"""WebChannel streaming client and protocol helpers for Dialogflow."""

import json
import logging
import queue
import random
import re
import threading
import urllib.parse

import google.auth
from google.auth.transport.requests import AuthorizedSession

try:
    CREDENTIALS, PROJECT_ID = google.auth.default(
        scopes=["https://www.googleapis.com/auth/dialogflow"])
except Exception:  # pylint: disable=broad-exception-caught
    CREDENTIALS = None

COMMON_HEADERS = {
    "X-Goog-Api-Client": "gl-python",
}

WEBCHANNEL_POST_HEADERS = {
    "X-WebChannel-Content-Type": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    **COMMON_HEADERS,
}

STOP_SIGNAL = "STOP"

# Timeout tuples: (connect_timeout_seconds, read_timeout_seconds)
# - INIT_TIMEOUT: 10s to connect, 30s to receive handshake response.
INIT_TIMEOUT = (10.0, 30.0)
# - POST_TIMEOUT: 10s to connect, 10s to transmit upstream RPC message.
POST_TIMEOUT = (10.0, 10.0)
# - GET_TIMEOUT: 10s to connect, 60s idle read timeout for stream chunks.
GET_TIMEOUT = (10.0, 60.0)

WEBCHANNEL_SID_REGEX = re.compile(r'\[\s*"c"\s*,\s*"([^"]+)"')


def get_webchannel_post_headers(token: str) -> dict:
    """Builds HTTP POST headers required for WebChannel message delivery."""
    return {
        "Authorization": f"Bearer {token}",
        **WEBCHANNEL_POST_HEADERS,
    }


def get_webchannel_get_headers(token: str) -> dict:
    """Builds HTTP GET headers for long-poll WebChannel chunk consumption."""
    return {
        "Authorization": f"Bearer {token}",
        **COMMON_HEADERS,
    }


def create_webchannel_init_url(endpoint_url: str, init_rid: int) -> str:
    """Constructs the WebChannel handshake initialization URL."""
    return (f"{endpoint_url}?VER=8&MODE=init&RID={init_rid}&"
            "X-HTTP-Session-Id=gsessionid")


def create_webchannel_post_url(endpoint_url: str, rid: int, webchannel_sid: str,
                               gsessionid: str) -> str:
    """Constructs the WebChannel message delivery POST URL."""
    return (f"{endpoint_url}?VER=8&RID={rid}&SID={webchannel_sid}&"
            f"gsessionid={gsessionid}&AID=0")


def create_webchannel_get_url(endpoint_url: str, webchannel_sid: str,
                              gsessionid: str) -> str:
    """Constructs the WebChannel chunked streaming GET URL."""
    return (f"{endpoint_url}?VER=8&RID=rpc&SID={webchannel_sid}&"
            f"gsessionid={gsessionid}&AID=0&CI=0&TYPE=xmlhttp")


def extract_webchannel_sid(response_text: str) -> str:
    """Extracts the session SID from WebChannel init handshake response."""
    match = WEBCHANNEL_SID_REGEX.search(response_text)
    return match.group(1) if match else None


def get_streaming_rpc_url(channel_path: str, location: str) -> str:
    """Resolves the regionalized OnePlatform WebChannel endpoint URL."""
    prefix = f"https://{location}-dialogflow-webchannel.googleapis.com/"
    return f"{prefix}{channel_path}"


def _format_webchannel_message(requests, ofs=0, count=None):
    """Encodes a JSON RPC payload into WebChannel form-urlencoded format."""
    req_list = requests if isinstance(requests, list) else [requests]
    msg_count = count if count is not None else len(req_list)
    data_params = [
        f"req{i}___data__={urllib.parse.quote(json.dumps(r))}"
        for i, r in enumerate(req_list)
    ]
    return f"count={msg_count}&ofs={ofs}&" + "&".join(data_params)


def _snake_to_camel_key(key: str) -> str:
    components = key.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def snake_to_camel(obj):
    """Recursively converts snake_case keys in dicts/lists to camelCase."""
    if isinstance(obj, dict):
        return {
            _snake_to_camel_key(k): snake_to_camel(v) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [snake_to_camel(item) for item in obj]
    return obj


def _extract_webchannel_chunks(buffer: str) -> tuple[list[str], str]:
    """Buffers incoming TCP data and parses length-prefixed chunks."""
    chunks = []
    while True:
        newline_idx = buffer.find("\n")
        if newline_idx == -1:
            break
        size_str = buffer[:newline_idx].strip()
        if size_str.isdigit():
            size = int(size_str)
            if len(buffer) < newline_idx + 1 + size:
                break
            chunks.append(buffer[newline_idx + 1:newline_idx + 1 + size])
            buffer = buffer[newline_idx + 1 + size:]
        else:
            buffer = buffer[newline_idx + 1:]
    return chunks, buffer


def _decode_webchannel_payload(chunk_text: str) -> list[dict]:
    """Decodes length-delimited JSON frames and maps keys for UI modules."""
    try:
        data_list = json.loads(chunk_text)
        results = []
        for frame in data_list:
            payload = frame[1][0]
            if isinstance(payload, dict) and "error" in payload:
                err_msg = payload["error"].get("message", str(payload["error"]))
                results.append({"type": "error", "payload": err_msg})
            elif (isinstance(payload, list) and payload and
                  "error" in payload[0]):
                err_msg = payload[0]["error"].get("message",
                                                  str(payload[0]["error"]))
                results.append({"type": "error", "payload": err_msg})
            else:
                results.append({
                    "type": "data",
                    "payload": snake_to_camel(payload)
                })
        return results
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.exception("Failed to parse WebChannel response: %s", e)
        return [{"type": "error", "payload": f"Error parsing response: {e}"}]


class WebChannelClient:
    """Event-driven client managing WebChannel streaming lifecycle."""

    def __init__(self, endpoint_url, credentials=None):
        self.endpoint_url = endpoint_url
        self.credentials = credentials or CREDENTIALS
        self.active_stream_queue = queue.Queue()
        self.on_response_cb = None
        self.on_error_cb = None
        self.on_close_cb = None
        self.stopped = False
        self.rid = 0
        self.message_offset = 0

    def onResponse(self, callback):  # pylint: disable=invalid-name
        """Registers a callback for receiving response payloads."""
        self.on_response_cb = callback

    def onError(self, callback):  # pylint: disable=invalid-name
        """Registers a callback for receiving streaming errors."""
        self.on_error_cb = callback

    def onClose(self, callback):  # pylint: disable=invalid-name
        """Registers a callback for stream closure events."""
        self.on_close_cb = callback

    def _emit_error(self, err_msg):
        logging.error("WebChannel Error: %s", err_msg)
        if self.on_error_cb:
            self.on_error_cb(err_msg)

    def _emit_data(self, payload):
        if self.on_response_cb:
            self.on_response_cb(payload)

    def connect(self):
        """Initializes worker thread for WebChannel streaming."""
        if not self.credentials:
            self._emit_error("No credentials available for AuthorizedSession.")
            return

        worker_thread = threading.Thread(target=self._stream_worker,
                                         daemon=True)
        worker_thread.start()

    def send(self, payload):
        """Buffers an upstream message payload to be dispatched."""
        if not self.stopped:
            self.active_stream_queue.put(payload)

    def close(self, reason: str):
        """Terminates active worker and reader threads."""
        if self.stopped:
            return
        self.stopped = True
        logging.info("WebChannel stream stopped (reason: %s)", reason)
        self.active_stream_queue.put(STOP_SIGNAL)
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.exception("Error in on_close callback: %s", e)

    def _perform_init(self, session, post_headers):
        init_rid = random.randint(10000, 99999)
        init_url = create_webchannel_init_url(self.endpoint_url, init_rid)
        init_resp = session.post(
            init_url,
            headers=post_headers,
            data="count=0",
            timeout=INIT_TIMEOUT,
        )
        if init_resp.status_code != 200:
            self._emit_error(
                f"WebChannel init failed with status {init_resp.status_code}:"
                f" {init_resp.text}")
            return None, None

        webchannel_sid = extract_webchannel_sid(init_resp.text)
        if not webchannel_sid:
            self._emit_error("No WebChannel SID extracted from init response:"
                             f" {init_resp.text}")
            return None, None

        gsessionid = (init_resp.headers.get("x-http-session-id") or
                      init_resp.headers.get("x-webchannel-session") or
                      webchannel_sid)
        return webchannel_sid, gsessionid

    def _do_post_requests(
        self,
        session,
        requests_to_send,
        post_headers,
        webchannel_sid,
        gsessionid,
    ):
        if not requests_to_send:
            return

        post_url = create_webchannel_post_url(self.endpoint_url, self.rid,
                                              webchannel_sid, gsessionid)
        post_resp = session.post(
            post_url,
            headers=post_headers,
            data=_format_webchannel_message(requests_to_send,
                                            ofs=self.message_offset),
            timeout=POST_TIMEOUT,
        )
        if post_resp.status_code != 200:
            self._emit_error("WebChannel POST request failed with status "
                             f"{post_resp.status_code}: {post_resp.text}")
        self.rid += 1
        self.message_offset += len(requests_to_send)

    def _stream_worker(self):
        session = None
        try:
            requests_to_send = []
            try:
                requests_to_send.append(
                    self.active_stream_queue.get(timeout=60))
            except queue.Empty:
                self.close(reason="initial_queue_timeout")
                return

            if requests_to_send[0] == STOP_SIGNAL:
                return

            while not self.active_stream_queue.empty():
                item = self.active_stream_queue.get_nowait()
                if item == STOP_SIGNAL:
                    return
                requests_to_send.append(item)

            session = AuthorizedSession(self.credentials)
            token = self.credentials.token if self.credentials else ""
            post_headers = get_webchannel_post_headers(token)

            webchannel_sid, gsessionid = self._perform_init(
                session, post_headers)
            if not webchannel_sid:
                self.close(reason="init_handshake_failed")
                return

            self.rid = random.randint(10000, 99999) + 1
            self.message_offset = 0
            self._do_post_requests(
                session,
                requests_to_send,
                post_headers,
                webchannel_sid,
                gsessionid,
            )

            get_url = create_webchannel_get_url(self.endpoint_url,
                                                webchannel_sid, gsessionid)
            get_headers = get_webchannel_get_headers(token)

            response = session.get(get_url,
                                   headers=get_headers,
                                   stream=True,
                                   timeout=GET_TIMEOUT)
            if response.status_code != 200:
                self._emit_error("WebChannel GET stream failed with status"
                                 f" {response.status_code}: {response.text}")
                self.close(reason=f"get_stream_http_{response.status_code}")
                return

            reader_thread = threading.Thread(
                target=self._read_webchannel_stream,
                args=(response,),
                daemon=True,
            )
            reader_thread.start()

            while not self.stopped:
                try:
                    item = self.active_stream_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                if item == STOP_SIGNAL:
                    break
                self._do_post_requests(
                    session,
                    [item],
                    post_headers,
                    webchannel_sid,
                    gsessionid,
                )

            response.close()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._emit_error(str(e))
            self.close(reason=f"worker_exception: {e}")
        finally:
            if session:
                session.close()

    def _read_webchannel_stream(self, response):
        try:
            buffer = ""
            for chunk_bytes in response.iter_content(chunk_size=None,
                                                     decode_unicode=True):
                if not chunk_bytes:
                    continue
                buffer += chunk_bytes
                chunks, buffer = _extract_webchannel_chunks(buffer)
                for chunk_text in chunks:
                    events = _decode_webchannel_payload(chunk_text)
                    for event in events:
                        if event["type"] == "error":
                            self._emit_error(event["payload"])
                            err_str = event["payload"]
                            self.close(
                                reason=f"server_error_payload: {err_str}")
                            return
                        self._emit_data(event["payload"])
            self.close(reason="remote_get_stream_eof")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.close(reason=f"reader_exception: {e}")
