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
"""Hermetic real-protocol integration test for Five9 mediastream-grpc.

Starts the real mediastream-grpc asyncio gRPC server on an ephemeral localhost
port and verifies gRPC Server Reflection advertises the Five9 Voice service.
"""

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

import grpc
from grpc_reflection.v1alpha import reflection_pb2
from grpc_reflection.v1alpha import reflection_pb2_grpc

REPO_ROOT = Path(__file__).resolve().parents[4]
GRPC_DIR = (REPO_ROOT / "aa-integration-backend" / "platforms" / "five9" /
            "mediastream-grpc")


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


class TestFive9MediaStreamGrpcSmoke(unittest.TestCase):
    """Boots the real Five9 gRPC server and verifies reflection over TCP."""

    def test_grpc_server_boots_and_advertises_voice_service(self) -> None:
        """Starts mediastream-grpc main.py and queries gRPC reflection."""
        port = _find_free_port()
        env = {
            **os.environ,
            "PORT": str(port),
            "PROJECT_ID": "integration-test-project",
            "LOG_LEVEL": "WARNING",
        }
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(GRPC_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            _wait_for_port("127.0.0.1", port, timeout=20.0)

            async def _list_services() -> list[str]:
                async with grpc.aio.insecure_channel(
                        f"127.0.0.1:{port}") as channel:
                    stub = reflection_pb2_grpc.ServerReflectionStub(channel)
                    req = reflection_pb2.ServerReflectionRequest(
                        list_services="")
                    services = []
                    async for resp in stub.ServerReflectionInfo(iter([req])):
                        for svc in resp.list_services_response.service:
                            services.append(svc.name)
                    return services

            services = asyncio.run(_list_services())
            self.assertTrue(
                any(name.endswith("Voice") for name in services),
                f"Expected Voice service in reflection list, got: {services}",
            )
        finally:
            _terminate_process(proc)


if __name__ == "__main__":
    unittest.main()
