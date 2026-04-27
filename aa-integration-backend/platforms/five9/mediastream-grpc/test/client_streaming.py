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

"""
Client script to test gRPC audio streaming.
Supports single or dual stream (Customer + Agent).
"""

import argparse
import asyncio
import logging
import time
import wave
import sys
import grpc
import os
from typing import AsyncGenerator

# Add proto directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../proto")))

import voice_pb2
import voice_pb2_grpc


def get_args():
    parser = argparse.ArgumentParser(description="Stream audio to gRPC server")
    parser.add_argument("--wav-file", type=str, help="Path to wav file (single stream)")
    parser.add_argument("--customer-wav", type=str, help="Path to customer wav file")
    parser.add_argument("--agent-wav", type=str, help="Path to agent wav file")
    parser.add_argument("--port", type=str, default="8080", help="Server port")
    parser.add_argument("--call-id", type=str, default=None, help="non-random Call ID")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    parser.add_argument("--secure", action="store_true", help="Use TLS gRPC channel")
    parser.add_argument("--duration", type=float, default=None, help="In seconds")
    parser.add_argument("--count", type=int, default=1, help="Concurrent conversations")
    return parser.parse_args()


async def generate_requests(
    wav_file: str,
    call_id: str,
    role: voice_pb2.StreamingConfig.CallLeg,
    duration: float | None = None,
    barrier: asyncio.Barrier | None = None,
) -> AsyncGenerator[voice_pb2.StreamingVoiceRequest, None]:
    """Generates StreamingVoiceRequest messages."""
    try:
        wf = wave.open(wav_file, "rb")
    except Exception as e:
        print(f"Failed to open wav file {wav_file}: {e}")
        return

    with wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        conversation_id = f"five9-{int(call_id):010d}"

        role_name = (
            "CUSTOMER" if role == voice_pb2.StreamingConfig.CUSTOMER else "AGENT"
        )
        print(
            f"[{conversation_id}][{role_name}] Reading {wav_file} (Channels: {n_channels}, Bytes/Sample: {sampwidth}, Rate: {framerate} Hz)",
            flush=True,
        )

        # 1. Send StreamingConfig
        config = voice_pb2.StreamingConfig(
            voice_config=voice_pb2.VoiceConfig(
                encoding=voice_pb2.VoiceConfig.LINEAR16, sample_rate_hertz=framerate
            ),
            vcc_call_id=call_id,
            call_leg=role,
        )
        yield voice_pb2.StreamingVoiceRequest(streaming_config=config)

        # 2. Wait for server response and synchronization
        if barrier:
            print(
                f"[{conversation_id}][{role_name}] Config sent. Waiting for sync...",
                flush=True,
            )
            try:
                # 10s timeout to prevent hanging
                await asyncio.wait_for(barrier.wait(), timeout=10)
                print(
                    f"[{conversation_id}][{role_name}] Synced! Starting audio...",
                    flush=True,
                )
            except asyncio.TimeoutError:
                print(
                    f"[{conversation_id}][{role_name}] Barrier timeout!",
                    flush=True,
                )
                return
            except Exception as e:
                print(
                    f"[{conversation_id}][{role_name}] Barrier broken or error: {e}",
                    flush=True,
                )
                return

        await asyncio.sleep(0.5)

        # 3. Stream Audio
        chunk_size = 4096
        bytes_per_second = framerate * sampwidth * n_channels
        total_bytes_sent = 0
        max_bytes = int(duration * bytes_per_second) if duration else float("inf")

        start_time = time.time()

        while total_bytes_sent < max_bytes:
            data = wf.readframes(chunk_size // (sampwidth * n_channels))
            if not data:
                # Loop audio if duration is longer than file
                wf.setpos(0)
                data = wf.readframes(chunk_size // (sampwidth * n_channels))

            yield voice_pb2.StreamingVoiceRequest(audio_content=data)
            total_bytes_sent += len(data)

            # Synchronize chunks across streams to prevent drift
            if barrier:
                try:
                    # 5s timeout to prevent hanging if one leg fails
                    await asyncio.wait_for(barrier.wait(), timeout=5)
                except asyncio.TimeoutError:
                    break
                except Exception:
                    break

            # Precise Real-time Synchronization
            elapsed_clock = time.time() - start_time
            expected_clock = total_bytes_produced / bytes_per_second if 'total_bytes_produced' in locals() else total_bytes_sent / bytes_per_second

            sleep_dur = expected_clock - elapsed_clock
            if sleep_dur > 0:
                await asyncio.sleep(sleep_dur)

            if (
                total_bytes_sent % (bytes_per_second * 10) < chunk_size
            ):  # Log every ~10 seconds
                print(
                    f"\n[{conversation_id}][{role_name}] Sent {total_bytes_sent / bytes_per_second:.1f}s audio...",
                    end="",
                )


async def stream_audio(
    target: str,
    wav_file: str,
    call_id: str,
    role: voice_pb2.StreamingConfig.CallLeg,
    duration: float | None = None,
    secure: bool = False,
    barrier: asyncio.Barrier | None = None,
) -> None:
    role_name = "CUSTOMER" if role == voice_pb2.StreamingConfig.CUSTOMER else "AGENT"
    channel_type = "Secure" if secure else "Insecure"
    conversation_id = f"five9-{int(call_id):010d}"
    print(
        f"[{conversation_id}][{role_name}] Connecting to {target} ({channel_type})...",
        flush=True,
    )

    if secure:
        creds = grpc.ssl_channel_credentials()
        channel = grpc.aio.secure_channel(target, creds)
    else:
        channel = grpc.aio.insecure_channel(target)

    async with channel:
        stub = voice_pb2_grpc.VoiceStub(channel)

        try:
            # Current grpc.aio implementation for bidirectional streaming:
            # method(request_iterator) -> returns Call (which is also an async iterator of responses)
            call = stub.StreamingVoice(
                generate_requests(wav_file, call_id, role, duration, barrier)
            )

            async for response in call:
                if response.HasField("status"):
                    if (
                        response.status.code
                        == voice_pb2.StreamingStatus.StatusCode.SUCCESS
                    ):
                        print(".", end="", flush=True)
                    else:
                        print(
                            f"[{conversation_id}][{role_name}] Status: {response.status.code} - {response.status.message}",
                            flush=True,
                        )
                if response.HasField("feedback"):
                    print(
                        f"[{conversation_id}][{role_name}] Feedback: {response.feedback}",
                        flush=True,
                    )
        except grpc.aio.AioRpcError as e:
            print(
                f"\n--- RPC Error Debug Trace [{conversation_id}][{role_name}] ---",
                flush=True,
            )
            print(f"Code:    {e.code()}", flush=True)
            print(f"Details: {e.details()}", flush=True)

            # This often contains the 'x-cloud-trace-context' or load balancer info
            if e.trailing_metadata():
                print(f"Trailing Metadata: {e.trailing_metadata()}", flush=True)

            # This helps distinguish between a clean 503 and a messy TCP reset
            print(f"Debug String: {e.debug_error_string()}", flush=True)
            print("---------------------------------------------------\n", flush=True)


async def start_single_call(
    target: str, args: argparse.Namespace, call_index: int
) -> None:
    call_id = args.call_id
    if call_id is None:
        call_id = f"{int(time.time())}{call_index}"

    barrier = None
    if args.customer_wav and args.agent_wav:
        barrier = asyncio.Barrier(2)

    tasks = []

    if args.customer_wav:
        tasks.append(
            stream_audio(
                target,
                args.customer_wav,
                call_id,
                voice_pb2.StreamingConfig.CUSTOMER,
                args.duration,
                args.secure,
                barrier,
            )
        )

    if args.agent_wav:
        tasks.append(
            stream_audio(
                target,
                args.agent_wav,
                call_id,
                voice_pb2.StreamingConfig.AGENT,
                args.duration,
                args.secure,
                barrier,
            )
        )

    await asyncio.gather(*tasks)


async def main() -> None:
    args = get_args()
    target = f"{args.host}:{args.port}"

    print(f"Launching {args.count} concurrent conversations...", flush=True)

    call_tasks = []
    for i in range(args.count):
        call_tasks.append(start_single_call(target, args, i))
        # Stagger start slightly?
        # await asyncio.sleep(0.1)

    # Run all calls
    await asyncio.gather(*call_tasks)


if __name__ == "__main__":
    # Suppress gRPC logging which can be verbose
    os.environ["GRPC_VERBOSITY"] = "ERROR"
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
