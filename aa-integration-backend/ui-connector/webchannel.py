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

import asyncio
import codecs
import json
import logging
import random
import re
import threading
from typing import Any
import urllib.parse

import aiohttp
import google.auth
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_auth_requests

try:
    CREDENTIALS, PROJECT_ID = google.auth.default(
        scopes=["https://www.googleapis.com/auth/dialogflow"])
except google_auth_exceptions.DefaultCredentialsError:
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

# Seconds to wait for the first upstream payload before abandoning a stream.
FIRST_MESSAGE_TIMEOUT = 60.0

# Timeouts: seconds to connect, then an idle (sock_read) timeout between reads.
# - INIT_TIMEOUT: 10s to connect, 30s to receive handshake response.
INIT_TIMEOUT = aiohttp.ClientTimeout(connect=10.0, sock_read=30.0)
# - POST_TIMEOUT: 10s to connect, 10s to transmit upstream RPC message.
POST_TIMEOUT = aiohttp.ClientTimeout(connect=10.0, sock_read=10.0)
# - GET_TIMEOUT: 10s to connect, 60s idle read timeout between backchannel
#   chunks. An idle timeout or EOF reconnects the backchannel GET instead of
#   closing the stream.
GET_TIMEOUT = aiohttp.ClientTimeout(connect=10.0, sock_read=60.0)

# Transient backchannel GET failures (connection errors, connect timeouts,
# credential refresh errors, 429/5xx) retry with exponential backoff
# (1s, 2s, 4s); frames received in between reset the retry budget. A GET that
# ends without delivering a frame (idle timeout or an immediate empty 200) also
# spends one retry so a misbehaving server cannot drive a tight reconnect loop.
BACKCHANNEL_MAX_RETRIES = 3
BACKCHANNEL_RETRY_BASE_SECONDS = 1.0
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

# Upper bound for one length-prefixed chunk; larger prefixes are treated as a
# corrupt stream instead of buffering without limit on the shared loop.
MAX_CHUNK_UTF16_UNITS = 4 * 1024 * 1024

WEBCHANNEL_SID_REGEX = re.compile(r'\[\s*"c"\s*,\s*"([^"]+)"')
# Dialogflow location ids; anything else must not reach the endpoint URL.
LOCATION_ID_REGEX = re.compile(r"[a-z0-9-]+")

# Serializes credential refreshes, which run on executor threads, so streams
# that share expired credentials trigger a single token request.
_REFRESH_LOCK = threading.Lock()


def get_webchannel_post_headers(token: str) -> dict[str, str]:
    """Builds HTTP POST headers required for WebChannel message delivery."""
    return {
        "Authorization": f"Bearer {token}",
        **WEBCHANNEL_POST_HEADERS,
    }


def get_webchannel_get_headers(token: str) -> dict[str, str]:
    """Builds HTTP GET headers for long-poll WebChannel chunk consumption."""
    return {
        "Authorization": f"Bearer {token}",
        **COMMON_HEADERS,
    }


def create_webchannel_init_url(endpoint_url: str, init_rid: int) -> str:
    """Constructs the WebChannel handshake initialization URL."""
    return (f"{endpoint_url}?VER=8&MODE=init&RID={init_rid}&"
            "X-HTTP-Session-Id=gsessionid")


def create_webchannel_post_url(endpoint_url: str,
                               rid: int,
                               webchannel_sid: str,
                               gsessionid: str,
                               aid: int = 0) -> str:
    """Constructs the WebChannel message delivery POST URL."""
    return (f"{endpoint_url}?VER=8&RID={rid}&SID={webchannel_sid}&"
            f"gsessionid={gsessionid}&AID={aid}")


def create_webchannel_get_url(endpoint_url: str,
                              webchannel_sid: str,
                              gsessionid: str,
                              aid: int = 0) -> str:
    """Constructs the WebChannel chunked streaming GET URL."""
    # AID acknowledges the last array id received so a reconnect resumes after
    # it; CI=0 keeps the backchannel chunked instead of closing it immediately.
    return (f"{endpoint_url}?VER=8&RID=rpc&SID={webchannel_sid}&"
            f"gsessionid={gsessionid}&AID={aid}&CI=0&TYPE=xmlhttp")


def extract_webchannel_sid(response_text: str) -> str:
    """Extracts the session SID from WebChannel init handshake response."""
    match = WEBCHANNEL_SID_REGEX.search(response_text)
    return match.group(1) if match else None


def get_streaming_rpc_url(channel_path: str, location: str) -> str:
    """Resolves the regionalized OnePlatform WebChannel endpoint URL."""
    # `location` is spliced into the host that receives the service account's
    # bearer token, so anything but a plain location id is rejected.
    if not LOCATION_ID_REGEX.fullmatch(location):
        raise ValueError(f"Invalid Dialogflow location: {location!r}")
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


def _utf16_chunk_end(buffer: str, start: int, size: int) -> int | None:
    """Returns the index just past `size` UTF-16 code units from `start`."""
    # The server counts chunk lengths in UTF-16 code units, so a character
    # above U+FFFF (such as an emoji) takes 2 units but 1 Python character.
    # A chunk spans at most `size` characters; encoding that many measures it
    # in the server's units, and None means it is still arriving. A prefix
    # that splits a surrogate pair keeps the whole character (surrogatepass).
    encoded = buffer[start:start + size].encode("utf-16-le", "surrogatepass")
    if len(encoded) < 2 * size:
        return None
    chunk = encoded[:2 * size].decode("utf-16-le", "surrogatepass")
    return start + len(chunk)


def _extract_webchannel_chunks(buffer: str) -> tuple[list[str], str]:
    """Buffers incoming TCP data and parses length-prefixed chunks."""
    # Raises ValueError when a length prefix exceeds MAX_CHUNK_UTF16_UNITS.
    chunks = []
    while True:
        newline_idx = buffer.find("\n")
        if newline_idx == -1:
            break
        size_str = buffer[:newline_idx].strip()
        if size_str.isdigit():
            size = int(size_str)
            if size > MAX_CHUNK_UTF16_UNITS:
                raise ValueError(f"WebChannel chunk of {size} units exceeds "
                                 f"the {MAX_CHUNK_UTF16_UNITS} unit limit")
            start = newline_idx + 1
            end = _utf16_chunk_end(buffer, start, size)
            if end is None:
                break
            chunks.append(buffer[start:end])
            buffer = buffer[end:]
        else:
            buffer = buffer[newline_idx + 1:]
    return chunks, buffer


def _credentials_need_refresh(credentials) -> bool:
    # `expired` already reports True 3m45s before the real expiry (google-auth's
    # REFRESH_THRESHOLD), so tokens are renewed with a buffer, not on failure.
    return not credentials.token or getattr(credentials, "expired", False)


def _refresh_credentials(credentials):
    """Refreshes `credentials` unless another stream already did."""
    with _REFRESH_LOCK:
        if _credentials_need_refresh(credentials):
            credentials.refresh(google_auth_requests.Request())


def _error_message(error_payload: dict[str, Any]) -> str:
    error = error_payload["error"]
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def _decode_webchannel_payload(chunk_text: str) -> list[dict[str, Any]]:
    """Decodes a chunk of `[aid, body]` frames into events tagged with `aid`."""
    # Data payloads are camelCased for UI modules; `noop` heartbeats, `stop` /
    # `close` control frames, and metadata objects get their own event types.
    try:
        results = []
        for aid, body in json.loads(chunk_text):
            if not isinstance(body, list):
                results.append({
                    "type": "metadata",
                    "aid": aid,
                    "payload": body
                })
                continue
            payload = body[0] if body else None
            if payload == "noop":
                results.append({"type": "noop", "aid": aid})
            elif payload in ("stop", "close"):
                results.append({
                    "type": "close",
                    "aid": aid,
                    "payload": payload
                })
            elif isinstance(payload, dict) and "error" in payload:
                results.append({
                    "type": "error",
                    "aid": aid,
                    "payload": _error_message(payload)
                })
            elif (isinstance(payload, list) and payload and
                  isinstance(payload[0], dict) and "error" in payload[0]):
                results.append({
                    "type": "error",
                    "aid": aid,
                    "payload": _error_message(payload[0])
                })
            else:
                results.append({
                    "type": "data",
                    "aid": aid,
                    "payload": snake_to_camel(payload)
                })
        return results
    except (TypeError, ValueError) as e:  # Not JSON, or not `[aid, body]`.
        logging.exception("Failed to parse WebChannel response: %s", e)
        return [{"type": "error", "payload": f"Error parsing response: {e}"}]


class WebChannelClient:
    """Event-driven client managing WebChannel streaming lifecycle.

    All network I/O runs as coroutines on one background event loop shared by
    every client in the process, so registered callbacks fire on that loop
    thread and must not block. Python code in a process ran on one core under
    the GIL before this change too; scale out with Gunicorn workers or
    instances.
    """

    _shared_loop: asyncio.AbstractEventLoop | None = None
    # Clients are built on Socket.IO handler threads, so the first-use loop
    # start below has to be guarded against two handlers racing.
    _shared_loop_lock = threading.Lock()

    def __init__(self, endpoint_url, credentials=None):
        self.endpoint_url = endpoint_url
        self.credentials = credentials or CREDENTIALS
        self.on_response_cb = None
        self.on_error_cb = None
        self.on_close_cb = None
        self.stopped = False
        self.rid = 0
        self.message_offset = 0
        # Latest WebChannel array id received; acknowledged on every request.
        self.last_aid = 0
        self._loop = self._get_shared_loop()
        self._outbound = asyncio.Queue()
        self._stream_future = None

    @classmethod
    def _get_shared_loop(cls) -> asyncio.AbstractEventLoop:
        """Returns the shared event loop, started on first use."""
        with cls._shared_loop_lock:
            if cls._shared_loop is None:
                cls._shared_loop = asyncio.new_event_loop()
                threading.Thread(target=cls._shared_loop.run_forever,
                                 name="webchannel-loop",
                                 daemon=True).start()
            return cls._shared_loop

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
        """Starts the WebChannel stream on the shared event loop."""
        if not self.credentials:
            self._emit_error("No credentials available for WebChannel stream.")
            self.close(reason="no_credentials")
            return

        self._stream_future = asyncio.run_coroutine_threadsafe(
            self._run_stream(), self._loop)

    def send(self, payload):
        """Queues an upstream message payload for the next POST."""
        if not self.stopped:
            self._loop.call_soon_threadsafe(self._outbound.put_nowait, payload)

    def close(self, reason: str):
        """Stops the stream and wakes the sender so it tears down its tasks."""
        if self.stopped:
            return
        self.stopped = True
        logging.info("WebChannel stream stopped (reason: %s)", reason)
        self._loop.call_soon_threadsafe(self._outbound.put_nowait, STOP_SIGNAL)
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.exception("Error in on_close callback: %s", e)

    async def _ensure_valid_token(self) -> str:
        """Returns a bearer token, refreshing expired credentials off-loop."""
        credentials = self.credentials
        # Unlocked fast path; `_refresh_credentials` re-checks under its lock so
        # concurrent streams that saw the same expiry trigger one refresh.
        if _credentials_need_refresh(credentials):
            await asyncio.get_running_loop().run_in_executor(
                None, _refresh_credentials, credentials)
        return credentials.token

    async def _next_batch(self, timeout=None) -> list[dict[str, Any]]:
        """Waits for queued payloads; returns [] once `close()` was called."""
        batch = [await asyncio.wait_for(self._outbound.get(), timeout)]
        while not self._outbound.empty():
            batch.append(self._outbound.get_nowait())
        return [] if STOP_SIGNAL in batch else batch

    async def _perform_init(self, session):
        """Runs the init handshake and returns (sid, gsessionid)."""
        token = await self._ensure_valid_token()
        init_rid = random.randint(10000, 99999)
        init_url = create_webchannel_init_url(self.endpoint_url, init_rid)
        async with session.post(
                init_url,
                headers=get_webchannel_post_headers(token),
                data="count=0",
                timeout=INIT_TIMEOUT,
        ) as init_resp:
            init_text = await init_resp.text()
            if init_resp.status != 200:
                self._emit_error(
                    f"WebChannel init failed with status {init_resp.status}:"
                    f" {init_text}")
                return None, None

            webchannel_sid = extract_webchannel_sid(init_text)
            if not webchannel_sid:
                self._emit_error("No WebChannel SID extracted from init "
                                 f"response: {init_text}")
                return None, None

            gsessionid = (init_resp.headers.get("x-http-session-id") or
                          init_resp.headers.get("x-webchannel-session") or
                          webchannel_sid)
            # Forward-channel request ids continue from the handshake's.
            self.rid = init_rid + 1
            return webchannel_sid, gsessionid

    async def _do_post_requests(self, session, requests_to_send, webchannel_sid,
                                gsessionid):
        """Sends queued payloads upstream; a rejected POST closes the stream."""
        token = await self._ensure_valid_token()
        post_url = create_webchannel_post_url(self.endpoint_url,
                                              self.rid,
                                              webchannel_sid,
                                              gsessionid,
                                              aid=self.last_aid)
        async with session.post(
                post_url,
                headers=get_webchannel_post_headers(token),
                data=_format_webchannel_message(requests_to_send,
                                                ofs=self.message_offset),
                timeout=POST_TIMEOUT,
        ) as post_resp:
            post_text = await post_resp.text()
            if post_resp.status != 200:
                self._emit_error("WebChannel POST request failed with status "
                                 f"{post_resp.status}: {post_text}")
                self.close(reason=f"post_http_{post_resp.status}")
                return
        self.rid += 1
        self.message_offset += len(requests_to_send)

    async def _run_stream(self):
        """Runs the handshake, then the backchannel reader and POST sender."""
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    requests_to_send = await self._next_batch(
                        FIRST_MESSAGE_TIMEOUT)
                except asyncio.TimeoutError:
                    self.close(reason="initial_queue_timeout")
                    return
                if not requests_to_send:  # Closed before the first payload.
                    return

                webchannel_sid, gsessionid = await self._perform_init(session)
                if not webchannel_sid:
                    self.close(reason="init_handshake_failed")
                    return

                reader = asyncio.create_task(
                    self._read_backchannel(session, webchannel_sid, gsessionid))
                try:
                    while requests_to_send:
                        await self._do_post_requests(session, requests_to_send,
                                                     webchannel_sid, gsessionid)
                        requests_to_send = await self._next_batch()
                finally:
                    reader.cancel()
                    await asyncio.gather(reader, return_exceptions=True)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._emit_error(str(e))
            self.close(reason=f"worker_exception: {e}")

    async def _read_backchannel(self, session, webchannel_sid, gsessionid):
        """Reads the hanging GET, reconnecting across EOF and idle timeouts."""
        retries = 0
        while True:
            aid_before = self.last_aid
            failure = None
            try:
                token = await self._ensure_valid_token()
                get_url = create_webchannel_get_url(self.endpoint_url,
                                                    webchannel_sid,
                                                    gsessionid,
                                                    aid=self.last_aid)
                async with session.get(
                        get_url,
                        headers=get_webchannel_get_headers(token),
                        timeout=GET_TIMEOUT,
                ) as response:
                    if response.status in _RETRYABLE_STATUSES:
                        failure = f"HTTP {response.status}"
                    elif response.status != 200:
                        self._emit_error(
                            "WebChannel GET stream failed with status"
                            f" {response.status}: {await response.text()}")
                        self.close(reason=f"get_stream_http_{response.status}")
                        return
                    elif await self._consume_backchannel(response):
                        return
            except aiohttp.SocketTimeoutError:
                # Idle backchannel: nothing arrived within the sock_read limit.
                failure = "idle"
            except (aiohttp.ClientError, asyncio.TimeoutError,
                    google_auth_exceptions.TransportError,
                    google_auth_exceptions.RefreshError) as e:
                # Compute Engine credentials (Cloud Run) report a failed
                # refresh as RefreshError rather than TransportError.
                failure = e
            except Exception as e:  # pylint: disable=broad-exception-caught
                self._emit_error(str(e))
                self.close(reason=f"reader_exception: {e}")
                return

            if self.last_aid > aid_before:
                # Frames arrived: a clean EOF or idle timeout after them is the
                # server's normal rotation, so reconnect at once with the budget
                # restored. Note that `_consume_backchannel` already returned
                # True on stop/close/error frames, so this is a real rotation.
                retries = 0
                if failure is None or failure == "idle":
                    logging.info(
                        "WebChannel backchannel GET ended; reconnecting with "
                        "AID=%s", self.last_aid)
                    continue
            retries += 1
            cause = failure or "EOF"
            if retries > BACKCHANNEL_MAX_RETRIES:
                self._emit_error("WebChannel GET stream failed after "
                                 f"{BACKCHANNEL_MAX_RETRIES} retries: {cause}")
                self.close(reason="backchannel_retries_exhausted")
                return
            delay = BACKCHANNEL_RETRY_BASE_SECONDS * 2**(retries - 1)
            logging.warning(
                "WebChannel backchannel GET ended without frames (%s); "
                "retry %d/%d in %.1fs", cause, retries, BACKCHANNEL_MAX_RETRIES,
                delay)
            await asyncio.sleep(delay)

    async def _consume_backchannel(self, response) -> bool:
        """Dispatches frames until EOF; True once a frame ends the stream."""
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        buffer = ""
        async for data in response.content.iter_any():
            buffer += decoder.decode(data)
            chunks, buffer = _extract_webchannel_chunks(buffer)
            for chunk_text in chunks:
                for event in _decode_webchannel_payload(chunk_text):
                    if self._handle_event(event):
                        return True
        return False

    def _handle_event(self, event) -> bool:
        """Applies one decoded frame; True when it terminates the stream."""
        aid = event.get("aid")
        if isinstance(aid, int) and aid > self.last_aid:
            self.last_aid = aid
        if event["type"] == "data":
            self._emit_data(event["payload"])
        elif event["type"] == "error":
            payload = event["payload"]
            self._emit_error(payload)
            self.close(reason=f"server_error_payload: {payload}")
            return True
        elif event["type"] == "close":
            payload = event["payload"]
            self.close(reason=f"server_{payload}_frame")
            return True
        elif event["type"] == "metadata":
            logging.debug("Ignoring WebChannel metadata frame: %s",
                          event["payload"])
        return False
