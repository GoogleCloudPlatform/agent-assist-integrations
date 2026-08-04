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

import sys
import os
import time
import wave
import grpc
import grpc.experimental.gevent as grpc_gevent
import requests
from locust import User, task, events, constant
from gevent.pool import Group
from gevent import sleep

# 1. Patch gRPC for Locust's gevent loop
grpc_gevent.init_gevent()

# Add proto path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../proto")))
import voice_pb2 as pb2  # type: ignore
import voice_pb2_grpc as pb2_grpc  # type: ignore


# --- Global Metric Setup ---
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    # Initialize a custom counter for total reconnects across the cluster
    environment.total_reconnects = 0


class VoiceLoadUser(User):
    wait_time = constant(1)

    def on_start(self):
        base_host = self.host.replace("https://", "").replace("http://", "")
        self.target = base_host if ":" in base_host else f"{base_host}:443"
        self.audience = f"https://{self.target.split(':')[0]}"

        # self.customer_wav = "../audio/END_USER_google_store.wav"
        # self.agent_wav = "../audio/HUMAN_AGENT_google_store.wav"
        self.customer_wav = "../audio/END_USER_all_transcripts_combined.wav"
        self.agent_wav = "../audio/HUMAN_AGENT_all_transcripts_combined.wav"

        # Fetch ID token once per User session to reduce metadata server load
        metadata_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={self.audience}"
        metadata_headers = {"Metadata-Flavor": "Google"}
        token_response = requests.get(metadata_url, headers=metadata_headers)
        token_response.raise_for_status()
        id_token = token_response.text

        call_credentials = grpc.access_token_call_credentials(id_token)
        ssl_credentials = grpc.ssl_channel_credentials()
        composite_credentials = grpc.composite_channel_credentials(
            ssl_credentials, call_credentials
        )

        self.channel = grpc.secure_channel(self.target, composite_credentials)
        self.stub = pb2_grpc.VoiceStub(self.channel)

    def on_stop(self):
        if hasattr(self, "channel") and self.channel:
            self.channel.close()

    def audio_generator(self, wav_path, role, leg_name, call_id):
        with wave.open(wav_path, "rb") as wf:
            framerate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            bytes_per_sec = framerate * sampwidth
            chunk_size = 4096

            yield pb2.StreamingVoiceRequest(
                streaming_config=pb2.StreamingConfig(
                    voice_config=pb2.VoiceConfig(
                        encoding=pb2.VoiceConfig.LINEAR16, sample_rate_hertz=framerate
                    ),
                    vcc_call_id=str(call_id),
                    call_leg=role,
                )
            )

            total_sent = 0
            start_time = time.time()

            while self.environment.runner.state not in ["stopping", "stopped"]:
                data = wf.readframes(chunk_size // sampwidth)
                if not data:
                    wf.setpos(0)
                    continue

                yield pb2.StreamingVoiceRequest(audio_content=data)
                total_sent += len(data)

                expected_time = total_sent / bytes_per_sec
                elapsed_time = time.time() - start_time
                sleep_dur = expected_time - elapsed_time

                if sleep_dur > 0:
                    sleep(sleep_dur)
                elif abs(sleep_dur) > 1.0:
                    events.request.fire(
                        request_type="gRPC-Lag",
                        name=f"{leg_name}_RealTime_Drift",
                        response_time=abs(sleep_dur) * 1000,
                        response_length=0,
                        exception=RuntimeError("Client lagging behind real-time"),
                    )

            # After the loop finishes (i.e., when the runner is stopping), send a graceful shutdown message.
            yield pb2.StreamingVoiceRequest(
                streaming_status=pb2.StreamingStatus(
                    code=pb2.StreamingStatus.CLT_DISCONNECT,
                    message="Locust user stopping.",
                )
            )

    def run_leg(self, wav_path, role, leg_name, call_id):
        conv_start_time = time.perf_counter()

        while self.environment.runner.state not in ["stopping", "stopped"]:
            request_start_time = time.perf_counter()

            try:
                responses = self.stub.StreamingVoice(
                    self.audio_generator(wav_path, role, leg_name, call_id)
                )

                # Handle the first response separately to measure TTFA
                try:
                    first_response = next(responses)
                    first_ack_time = time.perf_counter()
                    ttfa = (first_ack_time - request_start_time) * 1000
                    events.request.fire(
                        request_type="gRPC-Downlink",
                        name=f"{leg_name}_TimeToFirstAck",
                        response_time=ttfa,
                        response_length=first_response.ByteSize(),
                    )
                    last_ack_time = first_ack_time
                except StopIteration:
                    # This happens if the stream is empty.
                    break

                # Process subsequent responses for inter-arrival time
                for response in responses:
                    now = time.perf_counter()
                    inter_arrival_latency = (now - last_ack_time) * 1000
                    events.request.fire(
                        request_type="gRPC-Downlink",
                        name=f"{leg_name}_Ack_Interval",
                        response_time=inter_arrival_latency,
                        response_length=response.ByteSize(),
                    )
                    last_ack_time = now

                    if self.environment.runner.state in ["stopping", "stopped"]:
                        break

                # Clean exit if stream finishes
                break

            except (grpc.RpcError, Exception) as e:
                is_cancelled = (
                    isinstance(e, grpc.RpcError)
                    and e.code() == grpc.StatusCode.CANCELLED
                )

                if not is_cancelled:
                    # Increment the shared counter for observability
                    self.environment.total_reconnects += 1

                    events.request.fire(
                        request_type="gRPC-Event",
                        name=f"{leg_name}_Reconnect_Count_{self.environment.total_reconnects}",
                        response_time=0,
                        response_length=0,
                        exception=e,
                    )
                    sleep(0.5)
                else:
                    break

        total_duration = (time.perf_counter() - conv_start_time) * 1000
        events.request.fire(
            request_type="gRPC-Summary",
            name=f"{leg_name}_Total_Conversation_Duration",
            response_time=total_duration,
            response_length=0,
        )

    @task
    def dual_stream_conversation(self):
        call_id = str(time.perf_counter_ns())
        group = Group()
        group.spawn(
            self.run_leg,
            self.customer_wav,
            pb2.StreamingConfig.CUSTOMER,
            "Customer",
            call_id,
        )
        group.spawn(
            self.run_leg, self.agent_wav, pb2.StreamingConfig.AGENT, "Agent", call_id
        )
        group.join()
