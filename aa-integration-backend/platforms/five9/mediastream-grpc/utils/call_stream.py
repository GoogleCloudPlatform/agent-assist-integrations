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

"""Service implementation for Five9 VoiceStream."""

import logging
import asyncio
from collections import deque
from typing import Generator

import grpc
from google.api_core.exceptions import DeadlineExceeded
from voice_pb2 import StreamingVoiceRequest


class CallStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(
        self,
        input_generator: Generator[StreamingVoiceRequest, None, None],
        conversation_id: str,
        role: str,
        sample_rate: int = 16000,
        bit_depth: int = 16,
        max_lookback: int = 3,
        restart_timeout: int = 110,
        chunk_size: int = 1024,
        debug_logs: bool = False,
    ):
        self.input_generator = input_generator
        self.conversation_id = conversation_id
        self.role = role
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

        self.is_final = False
        self.closed = False
        self.terminate = False
        self.restart_timeout = restart_timeout
        self.restart_counter = 0  # Times the stream has half-closed and restarted.
        self.last_start_time = 0  # Ms since is_final since last_start_time.
        self.is_final_offset = 0  # Ms since is_final relative to last_start_time.

        max_chunks = int(sample_rate * 2 * max_lookback / chunk_size * 1.2)
        self.audio_input_chunks = deque([], maxlen=max_chunks)
        self.new_stream = True
        self.debug_logs = debug_logs

        self.disconnect_received = False
        self.error = None
        self.cancelled = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.closed = True
        self.terminate = True
        self.audio_input_chunks.clear()

    async def generator(self):
        try:
            if self.is_final:
                bytes_to_drop = int(
                    self.is_final_offset * self.sample_rate * self.bit_depth / 8 / 1000
                )
                if bytes_to_drop > 0:
                    current_buffer = b"".join(self.audio_input_chunks)
                    new_tail = current_buffer[bytes_to_drop:]
                    self.audio_input_chunks.clear()
                    if new_tail:
                        self.audio_input_chunks.append(new_tail)

            self.is_final = False
            if self.audio_input_chunks:
                yield b"".join(self.audio_input_chunks)

            bytes_sent = 0
            limit_bytes = self.restart_timeout * self.sample_rate * self.bit_depth / 8

            try:
                async for content in self.input_generator:
                    if self.closed or self.is_final:
                        break

                    if (
                        content.HasField("streaming_status")
                        and content.streaming_status.code == 2001
                    ):
                        logging.info(
                            f"[{self.conversation_id}][{self.role}]: Received Disconnect message. Closing stream."
                        )
                        self.closed = True
                        self.terminate = True
                        self.disconnect_received = True
                        break

                    if content.audio_content:
                        self.audio_input_chunks.append(content.audio_content)
                        chunk_len = len(content.audio_content)
                        bytes_sent += chunk_len
                        yield content.audio_content

                    if bytes_sent > limit_bytes:
                        duration_ms = (
                            bytes_sent / self.sample_rate * self.bit_depth / 8 * 1000
                        )
                        self.is_final_offset = duration_ms
                        self.is_final = True
                        break
            except asyncio.CancelledError:
                logging.info(
                    f"[{self.conversation_id}][{self.role}]: Stream cancelled."
                )
                self.closed = True
                self.terminate = True
                self.cancelled = True
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                    logging.warning(
                        f"[{self.conversation_id}][{self.role}]: Deadline Exceeded, restarting stream."
                    )
                    self.is_final = True
                else:
                    raise e
            except Exception as e:
                logging.error(
                    f"[{self.conversation_id}][{self.role}]: Stream error: {e}"
                )
                self.closed = True
                self.terminate = True
                self.error = e

            if not self.closed and not self.is_final:
                self.closed = True
        finally:
            if self.debug_logs:
                logging.debug(
                    f"[{self.conversation_id}][{self.role}]: CallStream.generator stopped - "
                    + f"last_start_time: {self.last_start_time}, "
                    + f"is_final_offset: {self.is_final_offset}, "
                    + f"restart_counter: {self.restart_counter}",
                )
