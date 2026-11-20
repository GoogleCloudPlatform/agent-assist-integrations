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
"""Hermetic real-protocol integration test for Five9 mediastream-http.

Starts the real mediastream-http Gunicorn process and verifies health check,
CTI x-api-key + SHA-256 trust token validation, and UI Modules token fetch
against a real local mock ui-connector /register HTTP server.
"""

import hashlib
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest

import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
HTTP_DIR = (REPO_ROOT / "aa-integration-backend" / "platforms" / "five9" /
            "mediastream-http")


def _find_free_port() -> int:
    """Binds to port 0 to obtain an available localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_http(url: str, timeout: float = 20.0) -> requests.Response:
    """Polls an HTTP endpoint until it returns a 2xx response."""
    deadline = time.monotonic() + timeout
    last_err = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=1.0)
            if 200 <= resp.status_code < 300:
                return resp
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


class TestFive9MediaStreamHttpSmoke(unittest.TestCase):
    """Boots the real Five9 HTTP server under Gunicorn and exercises routes."""

    trust_token = "five9-smoke-trust-token-secret"
    api_key = "five9-smoke-api-key"

    def test_http_health_cti_validation_and_ui_modules_register(self) -> None:
        """Exercises health, CTI API-key/SHA-256 auth, and /register call."""
        received_auth_headers: list[str] = []

        class _MockUiConnectorHandler(BaseHTTPRequestHandler):
            """Minimal mock ui-connector /register server."""

            def do_POST(self):  # pylint: disable=invalid-name
                if self.path == "/register":
                    received_auth_headers.append(
                        self.headers.get("Authorization", ""))
                    body = json.dumps({
                        "token": "mock-jwt-from-ui-connector"
                    }).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):  # pylint: disable=redefined-builtin
                del format, args

        mock_server = HTTPServer(("127.0.0.1", 0), _MockUiConnectorHandler)
        mock_port = mock_server.server_address[1]
        mock_thread = threading.Thread(
            target=mock_server.serve_forever,
            daemon=True,
        )
        mock_thread.start()

        http_port = _find_free_port()
        base_url = f"http://127.0.0.1:{http_port}"
        env = {
            **os.environ,
            "PORT": str(http_port),
            "FIVE9_TRUST_TOKEN": self.trust_token,
            "FIVE9_API_KEY": self.api_key,
            "UI_CONNECTOR_URL": f"http://127.0.0.1:{mock_port}",
            "CONVERSATION_PROFILE_NAME":
                ("projects/p/locations/global/conversationProfiles/cp1"),
            "FEATURES": "SMART_REPLY",
        }
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "--no-control-socket",
                "--bind",
                f"127.0.0.1:{http_port}",
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
            cwd=str(HTTP_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            health = _wait_for_http(f"{base_url}/", timeout=20.0)
            self.assertEqual(health.status_code, 200)
            self.assertIn("Five9 MediaStream HTTP Service Available",
                          health.text)

            expected_sha = hashlib.sha256(
                self.trust_token.encode("utf-8")).hexdigest()
            cti_ok = requests.get(
                f"{base_url}/cti-call-event-destination/",
                headers={"x-api-key": self.api_key},
                timeout=5.0,
            )
            self.assertEqual(cti_ok.status_code, 200)
            self.assertEqual(cti_ok.json(), expected_sha)

            cti_bad = requests.get(
                f"{base_url}/cti-call-event-destination/",
                headers={"x-api-key": "wrong-key"},
                timeout=5.0,
            )
            self.assertEqual(cti_bad.status_code, 401)

            page = requests.get(
                f"{base_url}/agent-assist-ui-modules/",
                timeout=5.0,
            )
            self.assertEqual(page.status_code, 200)
            self.assertIn("mock-jwt-from-ui-connector", page.text)
            self.assertEqual(
                received_auth_headers,
                [f"Bearer {self.trust_token}"],
            )
        finally:
            _terminate_process(proc)
            mock_server.shutdown()
            mock_server.server_close()


if __name__ == "__main__":
    unittest.main()
