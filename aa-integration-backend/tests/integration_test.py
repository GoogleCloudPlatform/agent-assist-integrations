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
"""Hermetic real-protocol integration tests for aa-integration-backend.

Exercises real Gunicorn processes for ui-connector and cloud-pubsub-interceptor
backed by a real Redis instance, a real python-socketio client over WebSocket,
real HTTP CORS/JWT flows, and a real local aiohttp WebChannel server.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from aiohttp import web
import requests
import socketio

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_CONNECTOR_DIR = REPO_ROOT / "aa-integration-backend" / "ui-connector"
PUBSUB_DIR = REPO_ROOT / "aa-integration-backend" / "cloud-pubsub-interceptor"


def _find_free_port() -> int:
    """Binds to port 0 to obtain an available localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> None:
    """Polls until a TCP port accepts connections or raises TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for {host}:{port}")


def _wait_for_http(url: str,
                   timeout: float = 20.0,
                   allow_any: bool = False) -> None:
    """Polls an HTTP endpoint until it returns a 2xx (or any) response."""
    deadline = time.monotonic() + timeout
    last_err = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=1.0)
            if allow_any or 200 <= resp.status_code < 300:
                return
        except requests.RequestException as exc:
            last_err = exc
        time.sleep(0.15)
    raise TimeoutError(f"Timed out waiting for {url} (last error: {last_err})")


def _terminate_process(proc: subprocess.Popen | None) -> None:
    """Gracefully terminates a subprocess, escalating to kill if needed."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _utf16_len(text: str) -> int:
    """Returns UTF-16 code unit length matching Google WebChannel framing."""
    return len(text.encode("utf-16-le")) // 2


def _webchannel_chunk(*frames) -> bytes:
    """Formats `[aid, body]` frames with WebChannel UTF-16 length prefix."""
    payload = json.dumps(list(frames), ensure_ascii=False)
    return f"{_utf16_len(payload)}\n{payload}".encode("utf-8")


class _RedisFixture:
    """Provides a real Redis endpoint via env var, local binary, or Docker."""

    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 0
        self._proc: subprocess.Popen | None = None
        self._docker_container: str | None = None

    def start(self) -> None:
        """Starts or connects to a real Redis server."""
        env_host = os.environ.get("INTEGRATION_REDIS_HOST")
        env_port = os.environ.get("INTEGRATION_REDIS_PORT")
        if env_host and env_port:
            self.host = env_host
            self.port = int(env_port)
            _wait_for_port(self.host, self.port, timeout=10.0)
            return

        self.port = _find_free_port()
        redis_bin = shutil.which("redis-server")
        if redis_bin:
            self._proc = subprocess.Popen(
                [
                    redis_bin,
                    "--bind",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                    "--save",
                    "",
                    "--appendonly",
                    "no",
                    "--loglevel",
                    "warning",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _wait_for_port(self.host, self.port, timeout=10.0)
            return

        docker_bin = shutil.which("docker")
        if docker_bin:
            name = f"aa-integration-redis-{self.port}"
            subprocess.run(
                [
                    docker_bin,
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    name,
                    "-p",
                    f"127.0.0.1:{self.port}:6379",
                    "redis:7-alpine",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._docker_container = name
            _wait_for_port(self.host, self.port, timeout=20.0)
            return

        raise unittest.SkipTest(
            "Real Redis unavailable (install redis-server, docker, "
            "or set INTEGRATION_REDIS_HOST/INTEGRATION_REDIS_PORT).")

    def stop(self) -> None:
        """Stops any Redis server spawned by this fixture."""
        _terminate_process(self._proc)
        if self._docker_container:
            subprocess.run(
                ["docker", "rm", "-f", self._docker_container],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )


class TestCoreBackendRealProtocol(unittest.TestCase):
    """Real-process integration tests for ui-connector + pubsub interceptor."""

    redis_fixture: _RedisFixture
    temp_dir: tempfile.TemporaryDirectory
    ui_proc: subprocess.Popen
    pubsub_proc: subprocess.Popen
    ui_url: str
    pubsub_url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.redis_fixture = _RedisFixture()
        cls.redis_fixture.start()

        secret_path = Path(cls.temp_dir.name) / "jwt_secret_key"
        secret_path.write_text(
            "integration-test-jwt-secret-key-at-least-32-bytes!",
            encoding="utf-8",
        )
        adc_path = Path(cls.temp_dir.name) / "adc.json"
        adc_path.write_text(
            json.dumps({
                "type": "authorized_user",
                "client_id": "integration-test",
                "client_secret": "integration-test",
                "refresh_token": "integration-test",
                "quota_project_id": "integration-test-project",
            }),
            encoding="utf-8",
        )

        ui_port = _find_free_port()
        pubsub_port = _find_free_port()
        cls.ui_url = f"http://127.0.0.1:{ui_port}"
        cls.pubsub_url = f"http://127.0.0.1:{pubsub_port}"

        ui_env = {
            **os.environ,
            "GOOGLE_APPLICATION_CREDENTIALS": str(adc_path),
            "GCP_PROJECT_ID": "integration-test-project",
            "REDISHOST": cls.redis_fixture.host,
            "REDISPORT": str(cls.redis_fixture.port),
            "AUTH_OPTION": "Skip",
            "JWT_SECRET_KEY_PATH": str(secret_path),
            "LOGGING_FILE": str(Path(cls.temp_dir.name) / "ui-connector.log"),
        }
        cls.ui_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "--bind",
                f"127.0.0.1:{ui_port}",
                "--workers",
                "1",
                "--threads",
                "8",
                "--graceful-timeout",
                "2",
                "--timeout",
                "0",
                "main:app",
            ],
            cwd=str(UI_CONNECTOR_DIR),
            env=ui_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        pubsub_env = {
            **os.environ,
            "GCP_PROJECT_ID": "integration-test-project",
            "REDISHOST": cls.redis_fixture.host,
            "REDISPORT": str(cls.redis_fixture.port),
            "LOGGING_FILE": str(Path(cls.temp_dir.name) / "pubsub.log"),
        }
        cls.pubsub_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "--bind",
                f"127.0.0.1:{pubsub_port}",
                "--workers",
                "1",
                "--threads",
                "4",
                "--graceful-timeout",
                "2",
                "--timeout",
                "0",
                "main:app",
            ],
            cwd=str(PUBSUB_DIR),
            env=pubsub_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            _wait_for_http(f"{cls.ui_url}/status", timeout=30.0)
            _wait_for_http(f"{cls.pubsub_url}/", timeout=30.0, allow_any=True)
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        _terminate_process(getattr(cls, "ui_proc", None))
        _terminate_process(getattr(cls, "pubsub_proc", None))
        if hasattr(cls, "redis_fixture"):
            cls.redis_fixture.stop()
        if hasattr(cls, "temp_dir"):
            cls.temp_dir.cleanup()

    def _register_jwt(self) -> str:
        """Obtains a real signed JWT from ui-connector /register."""
        resp = requests.post(
            f"{self.ui_url}/register",
            headers={"Authorization": "Bearer test-skip-token"},
            json={"gcp_agent_assist_user": "agent@example.com"},
            timeout=5.0,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        token = resp.json().get("token")
        self.assertTrue(token)
        return token

    def test_status_landing_page_and_cors_preflight(self) -> None:
        """Verifies real HTTP endpoints, Jinja2 template, and Flask-Cors."""
        status_resp = requests.get(
            f"{self.ui_url}/status",
            headers={"Origin": "https://agent-desktop.example.com"},
            timeout=5.0,
        )
        self.assertEqual(status_resp.status_code, 200)
        self.assertIn("Hello, cross-origin-world!", status_resp.text)
        self.assertIn("Access-Control-Allow-Origin", status_resp.headers)

        root_resp = requests.get(f"{self.ui_url}/", timeout=5.0)
        self.assertEqual(root_resp.status_code, 200)
        self.assertIn("<html", root_resp.text.lower())

        preflight = requests.options(
            f"{self.ui_url}/register",
            headers={
                "Origin": "https://agent-desktop.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
            timeout=5.0,
        )
        self.assertIn(preflight.status_code, (200, 204))
        self.assertIn("Access-Control-Allow-Origin", preflight.headers)

    def test_jwt_auth_and_conversation_name_redis_roundtrip(self) -> None:
        """Verifies PyJWT enforcement and Redis persistence via REST."""
        unauth = requests.get(
            f"{self.ui_url}/conversation-name",
            params={"conversationIntegrationKey": "key-1"},
            timeout=5.0,
        )
        self.assertEqual(unauth.status_code, 401)

        forged = requests.get(
            f"{self.ui_url}/conversation-name",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
            params={"conversationIntegrationKey": "key-1"},
            timeout=5.0,
        )
        self.assertEqual(forged.status_code, 401)

        token = self._register_jwt()
        auth_headers = {"Authorization": f"Bearer {token}"}
        conv_name = ("projects/integration-test-project/locations/global/"
                     "conversations/conv-redis-1")

        post_resp = requests.post(
            f"{self.ui_url}/conversation-name",
            headers=auth_headers,
            json={
                "conversationIntegrationKey": "key-redis-1",
                "conversationName": conv_name,
            },
            timeout=5.0,
        )
        self.assertEqual(post_resp.status_code, 200)

        get_resp = requests.get(
            f"{self.ui_url}/conversation-name",
            headers=auth_headers,
            params={"conversationIntegrationKey": "key-redis-1"},
            timeout=5.0,
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["conversationName"], conv_name)

        del_resp = requests.delete(
            f"{self.ui_url}/conversation-name",
            headers=auth_headers,
            params={"conversationIntegrationKey": "key-redis-1"},
            timeout=5.0,
        )
        self.assertEqual(del_resp.status_code, 200)

    def test_socketio_rejects_forged_jwt(self) -> None:
        """Verifies Socket.IO refuses connections without a valid JWT."""
        client = socketio.Client()
        try:
            with self.assertRaises(socketio.exceptions.ConnectionError):
                client.connect(
                    self.ui_url,
                    auth={"token": "forged.invalid.token"},
                    wait_timeout=5,
                )
        finally:
            if client.connected:
                client.disconnect()

    def test_pubsub_interceptor_to_redis_to_socketio_delivery(self) -> None:
        """Verifies end-to-end Pub/Sub -> Redis -> ui-connector -> Socket.IO."""
        token = self._register_jwt()
        conversation = ("projects/integration-test-project/locations/"
                        "us-central1/conversations/conv-e2e-42")
        expected_room = (
            "projects/integration-test-project/conversations/conv-e2e-42")

        received = []
        event_arrived = threading.Event()
        client = socketio.Client()

        @client.on("human-agent-assistant-event")
        def _on_suggestion(data):
            received.append(data)
            event_arrived.set()

        try:
            client.connect(
                self.ui_url,
                auth={"token": token},
                transports=["websocket"],
                wait_timeout=10,
            )
            join_ack = client.call(
                "join-conversation",
                conversation,
                timeout=5,
            )
            self.assertEqual(join_ack, (True, expected_room))

            suggestion_payload = {
                "conversation":
                    conversation,
                "participant":
                    f"{conversation}/participants/p1",
                "suggestionResults": [{
                    "suggestSmartRepliesResponse": {
                        "smartReplyAnswers": [{
                            "reply": "Hello from hermetic test!"
                        }]
                    }
                }],
            }
            encoded_data = base64.b64encode(
                json.dumps(suggestion_payload).encode("utf-8")).decode("utf-8")
            envelope = {
                "message": {
                    "data": encoded_data,
                    "messageId": "msg-smoke-001",
                    "publishTime": "2026-11-20T00:00:00Z",
                }
            }

            pubsub_resp = requests.post(
                f"{self.pubsub_url}/human-agent-assistant-event",
                json=envelope,
                timeout=5.0,
            )
            self.assertEqual(pubsub_resp.status_code, 204)

            self.assertTrue(
                event_arrived.wait(timeout=10.0),
                "Timed out waiting for Socket.IO event from Pub/Sub -> Redis",
            )
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]["conversation_name"], expected_room)
            self.assertEqual(received[0]["message_id"], "msg-smoke-001")
            self.assertEqual(json.loads(received[0]["data"]),
                             suggestion_payload)

            leave_ack = client.call(
                "leave-conversation",
                conversation,
                timeout=5,
            )
            self.assertEqual(leave_ack, (True, expected_room))
        finally:
            if client.connected:
                client.disconnect()


class TestWebChannelRealAiohttpProtocol(unittest.TestCase):
    """Tests webchannel.WebChannelClient against a real local aiohttp server."""

    def test_webchannel_handshake_forward_post_and_reconnect_stream(
        self,) -> None:
        """Exercises real aiohttp handshake, chunk framing, and EOF retry."""
        if str(UI_CONNECTOR_DIR) not in sys.path:
            sys.path.insert(0, str(UI_CONNECTOR_DIR))
        # pylint: disable=import-outside-toplevel
        import webchannel
        # pylint: enable=import-outside-toplevel

        forwarded_requests: list[str] = []
        get_attempts = {"count": 0}
        frame1_sent = asyncio.Event()

        async def _handle_channel(request: web.Request) -> web.StreamResponse:
            mode = request.query.get("MODE")
            if request.method == "POST" and mode == "init":
                return web.Response(
                    text='[[0,["c","sid-real-http","",8,14]]]',
                    headers={"X-HTTP-Session-Id": "gsession-real-http"},
                )

            if request.method == "POST":
                body = await request.text()
                forwarded_requests.append(body)
                return web.Response(text="ok")

            if request.method == "GET":
                get_attempts["count"] += 1
                resp = web.StreamResponse(status=200)
                await resp.prepare(request)
                if get_attempts["count"] == 1:
                    await resp.write(
                        _webchannel_chunk([
                            1, [{
                                "response_chunk": "first",
                                "is_final": False
                            }]
                        ]))
                    frame1_sent.set()
                    await resp.write_eof()
                    return resp
                if get_attempts["count"] == 2:
                    assert request.query.get("AID") == "1"
                    await resp.write(
                        _webchannel_chunk([
                            2, [{
                                "response_chunk": "second",
                                "is_final": True
                            }]
                        ]))
                    await asyncio.sleep(0.2)
                    await resp.write_eof()
                    return resp
                await asyncio.sleep(5)
                return resp

            return web.Response(status=405)

        server_ready = threading.Event()
        server_port = _find_free_port()
        stop_event_holder: dict[str, asyncio.Event] = {}
        server_loop_holder: dict[str, asyncio.AbstractEventLoop] = {}

        def _run_server() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server_loop_holder["loop"] = loop

            async def _serve() -> None:
                app = web.Application()
                app.router.add_route("*", "/channel", _handle_channel)
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, "127.0.0.1", server_port)
                await site.start()
                stop_ev = asyncio.Event()
                stop_event_holder["stop"] = stop_ev
                server_ready.set()
                await stop_ev.wait()
                await runner.cleanup()

            loop.run_until_complete(_serve())
            loop.close()

        server_thread = threading.Thread(target=_run_server, daemon=True)
        server_thread.start()
        self.assertTrue(server_ready.wait(timeout=5.0))

        endpoint = f"http://127.0.0.1:{server_port}/channel"
        responses = []
        errors = []
        two_responses = threading.Event()

        fake_creds = mock.MagicMock()
        fake_creds.token = "fake-bearer-token"
        fake_creds.expired = False

        client = webchannel.WebChannelClient(endpoint, credentials=fake_creds)
        client.onResponse(lambda payload: (
            responses.append(payload),
            two_responses.set() if len(responses) >= 2 else None,
        ))
        client.onError(errors.append)

        try:
            client.connect()
            client.send({"participant": "projects/p/locations/global"})
            self.assertTrue(
                two_responses.wait(timeout=10.0),
                f"Expected 2 frames; got responses={responses}, "
                f"errors={errors}",
            )
        finally:
            client.close(reason="integration_test_done")
            loop = server_loop_holder.get("loop")
            stop_ev = stop_event_holder.get("stop")
            if loop and stop_ev:
                loop.call_soon_threadsafe(stop_ev.set)
            server_thread.join(timeout=5.0)

        self.assertEqual(errors, [])
        self.assertEqual(
            responses,
            [
                {
                    "responseChunk": "first",
                    "isFinal": False
                },
                {
                    "responseChunk": "second",
                    "isFinal": True
                },
            ],
        )
        self.assertTrue(
            any("req0___data__" in body for body in forwarded_requests))


if __name__ == "__main__":
    unittest.main()
