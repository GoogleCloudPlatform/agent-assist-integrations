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

import logging
import asyncio
import os
import sys

import grpc.aio
from dotenv import load_dotenv

sys.path.append("proto")
import voice_pb2
from grpc_reflection.v1alpha import reflection
from services.get_suggestions import VoiceServicer
from voice_pb2_grpc import add_VoiceServicer_to_server


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("grpc._cython.cygrpc").setLevel(logging.ERROR)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

logging.info("Initializing gRPC Server...")
load_dotenv(".env")
server_port = os.getenv("PORT", "8080")

options = [
    ("grpc.keepalive_time_ms", 300000),  # Send a ping every 5 minutes
    ("grpc.keepalive_timeout_ms", 20000),  # Wait 20s for a pong before closing
    ("grpc.keepalive_permit_without_calls", 1),  # Allow pings even if no active RPCs
    ("grpc.http2.max_pings_without_data", 0),  # Allow unlimited pings
    (
        "grpc.http2.min_ping_interval_without_data_ms",
        120000,
    ),  # Allow clients to ping every 2 min
]


async def _serve(port: str):
    """Start gRPC server"""
    server = grpc.aio.server(options=options)
    add_VoiceServicer_to_server(VoiceServicer(), server)

    # Enable reflection
    SERVICE_NAMES = (
        voice_pb2.DESCRIPTOR.services_by_name["Voice"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    bind_address = f"0.0.0.0:{port}"
    server.add_insecure_port(bind_address)
    logging.info(f"Starting Server on {bind_address}")
    await server.start()
    logging.info(f"Server Started! Listening on {bind_address}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(_serve(server_port))
