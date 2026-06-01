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
import os
import grpc
import time

from typing import Generator
from dotenv import load_dotenv
import utils.call_stream as call_stream
import utils.conversation_management as conversation_management
import utils.participant_management as participant_management
import utils.conversation_profile_management as conversation_profile_management
from google.api_core.exceptions import DeadlineExceeded, Aborted, OutOfRange
from voice_pb2 import StreamingStatus, StreamingVoiceResponse, StreamingVoiceRequest
from voice_pb2_grpc import VoiceServicer

from google.cloud.dialogflow_v2beta1.types import AnalyzeContentResponse

load_dotenv(".env")

CONVERSATION_PROFILE_NAME = os.getenv("CONVERSATION_PROFILE_NAME", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")
RESTART_TIMEOUT = int(os.getenv("RESTART_TIMEOUT", 60 * 15 - 10))
RESTART_THRESHOLD = max(10, RESTART_TIMEOUT - 20)


class VoiceServicer(VoiceServicer):
    async def StreamingVoice(
        self,
        request_iterator: Generator[StreamingVoiceRequest, None, None],
        context: grpc.ServicerContext,
    ):
        """Streams audio to Dialogflow and returns suggestions."""
        request = await request_iterator.__anext__()

        try:
            streaming_config = request.streaming_config
            conversation_id = f"five9-{int(streaming_config.vcc_call_id):010d}"
            sample_rate = streaming_config.voice_config.sample_rate_hertz
            participant_role = (
                "END_USER" if streaming_config.call_leg == 1 else "HUMAN_AGENT"
            )
            log_prefix = f"[{conversation_id}][{participant_role}]"
            msg = f"{log_prefix}: Start sending audio!"
            logging.debug(f"Sent to client: {log_prefix}: {msg}")
            streaming_status = StreamingStatus(code=1001, message=msg)
            yield StreamingVoiceResponse(status=streaming_status)
        except Exception as e:
            msg = f"Config error: {e}"
            logging.error(f"Sent to client: {msg}")
            streaming_status = StreamingStatus(code=1102, message=msg)
            yield StreamingVoiceResponse(status=streaming_status)
            return

        conversation_profile = None
        try:
            conversation_profile = conversation_profile_management.get_conversation_profile(
                profile_name=CONVERSATION_PROFILE_NAME
            )
        except Exception as e:
            logging.debug(f"{log_prefix}: Error fetching conversation profile: {e}")

        conversation = None
        try:
            conversation = await conversation_management.get_conversation(
                project_id=PROJECT_ID,
                conversation_id=conversation_id,
            )
        except Exception as e:
            logging.debug(f"{log_prefix}: Error fetching conversation: {e}")

        if not conversation:
            logging.debug(f"{log_prefix}: Conversation not found. Creating...")
            try:
                conversation_profile_id = CONVERSATION_PROFILE_NAME.split("/")[-1]
                await conversation_management.create_conversation(
                    project_id=PROJECT_ID,
                    conversation_profile_id=conversation_profile_id,
                    conversation_id=conversation_id,
                )
            except Exception as e:
                msg = f"{log_prefix}: Conversation create error: {e}"
                logging.error(f"Sent to client: {msg}")
                streaming_status = StreamingStatus(code=1100, message=msg)
                yield StreamingVoiceResponse(status=streaming_status)
                return

        try:
            participant = await participant_management.create_participant(
                project_id=PROJECT_ID,
                conversation_id=conversation_id,
                role=participant_role,
            )
            if participant:
                participant_id = participant.name.split("participants/")[1].rstrip()
            else:
                raise Exception("Participant creation returned None")
        except Exception as e:
            msg = f"{log_prefix}: Participant create error: {e}"
            logging.error(f"Sent to client: {msg}")
            streaming_status = StreamingStatus(code=1100, message=msg)
            yield StreamingVoiceResponse(status=streaming_status)
            return

        call_stream_context_manager = call_stream.CallStream(
            input_generator=request_iterator,
            conversation_id=conversation_id,
            role=participant_role,
            sample_rate=sample_rate,
        )

        processing_error = False
        with call_stream_context_manager as stream:
            stream_start_time = time.time()
            while not stream.closed and not stream.terminate:
                try:
                    stream.restart_counter += 1
                    session_start_time = time.time()
                    responses = (
                        await participant_management.analyze_content_audio_stream(
                            project_id=PROJECT_ID,
                            conversation_id=conversation_id,
                            participant_id=participant_id,
                            sample_rate_hertz=sample_rate,
                            stream=stream,
                            timeout=RESTART_TIMEOUT,
                            language_code=conversation_profile.stt_config.language_code or "en-US",
                            single_utterance=False,
                        )
                    )

                    try:
                        async for response in responses:
                            yield StreamingVoiceResponse(
                                status=StreamingStatus(
                                    code=StreamingStatus.StatusCode.SUCCESS,
                                    message="Dialogflow response received.",
                                )
                            )
                            if stream.closed:
                                break
                            debug_analyze_content_response(
                                response,
                                conversation_id,
                                participant_role,
                                log_prefix,
                            )
                            if response.recognition_result.is_final:
                                offset = response.recognition_result.speech_end_offset
                                stream.is_final_offset = int(
                                    offset.seconds * 1000 + offset.microseconds / 1000
                                )
                                # Restart if the stream has been running for a while
                                if time.time() - session_start_time > RESTART_THRESHOLD:
                                    logging.debug(
                                        f"{log_prefix}: Restarting stream on final result after {time.time() - session_start_time:.2f}s"
                                    )
                                    stream.is_final = True

                    except (DeadlineExceeded, Aborted, OutOfRange):
                        raise
                    except Exception as e:
                        if "400 Conversation has completed." != str(e):
                            logging.debug(f"{log_prefix}: Stream error - {e}")

                        # Handle transient errors from Dialogflow or network infrastructure.
                        # 502/503 typically occur when intermediate load balancers cut long-running streams.
                        if any(x in str(e) for x in ["500", "502", "503", "Internal error", "Bad Gateway"]):
                            logging.warning(
                                f"{log_prefix}: Transient error {e}, retrying..."
                            )
                            continue

                        processing_error = True
                        break

                except DeadlineExceeded:
                    logging.warning(f"{log_prefix}: Deadline Exceeded, restarting. Total stream time: {time.time() - stream_start_time:.2f}s")
                except Aborted:
                    logging.warning(f"{log_prefix}: Stream aborted, restarting. Total stream time: {time.time() - stream_start_time:.2f}s")
                    stream.is_final = True
                    stream.is_error_restart = True
                except OutOfRange:
                    logging.warning(f"{log_prefix}: Stream out of range, restarting. Total stream time: {time.time() - stream_start_time:.2f}s")
                    stream.is_final = True
                    stream.is_error_restart = True
                except Exception as e:
                    # Handle transient errors during stream setup.
                    if any(x in str(e) for x in ["500", "502", "503", "Internal error", "Bad Gateway"]):
                        logging.warning(
                            f"{log_prefix}: Transient error {e} during stream setup, retrying..."
                        )
                        continue
                    logging.error(f"{log_prefix}: unhandled error in loop: {e}")
                    processing_error = True
                    break

        should_complete_conversation = False
        if not processing_error:
            if stream.disconnect_received:
                should_complete_conversation = True
                logging.info(
                    f"{log_prefix}: Completing conversation (Explicit disconnect received)"
                )
            elif not stream.cancelled and not stream.error:
                should_complete_conversation = True
                logging.info(
                    f"{log_prefix}: Completing conversation (Stream ended naturally)"
                )
            else:
                logging.info(
                    f"{log_prefix}: NOT Completing conversation (Stream error/cancelled)"
                )
        else:
            logging.info(
                f"{log_prefix}: NOT Completing conversation (Processing error encountered)"
            )

        if should_complete_conversation:
            await conversation_management.complete_conversation(
                project_id=PROJECT_ID, conversation_id=conversation_id
            )


def debug_analyze_content_response(
    response: AnalyzeContentResponse,
    conversation_id: str,
    participant_role: str,
    log_prefix: str,
    log_intermediate_transcripts: bool = False,
    log_suggestions: bool = False,
):
    # Handle the transcriptions
    if response.recognition_result:
        if response.recognition_result.is_final:
            logging.debug(
                f"{log_prefix}[final]: {response.recognition_result.transcript}"
            )
        # elif log_intermediate_transcripts and response.recognition_result.transcript:
        #     logging.debug(
        #         f"{log_prefix}[intermediate]: {response.recognition_result.transcript}"
        #     )

    # Handle the human agent suggestion results
    if log_suggestions and response.human_agent_suggestion_results:
        for suggestion in response.human_agent_suggestion_results:
            try:
                logging.debug(f"{log_prefix}: Agent Assist Suggestion: {suggestion}")
            except Exception as e:
                    logging.error(f"{log_prefix}: Error logging Agent Assist Suggestion: {e}")
