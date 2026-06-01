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

"""Referenced implementation from
https://github.com/GoogleCloudPlatform/python-docs-samples/blob/main/dialogflow/streaming_transcription.py
"""
import logging
import queue
import threading

import google.cloud.dialogflow_v2beta1 as dialogflow

from audiohook_config import config

MAX_BUFFER_SECONDS = 10
SINGLE_STREAM_MAX_DURATION = 90000
class Stream:
    """Opens a stream as a generator yielding the audio chunks.
    The generator method returns an iterator that contains subsequent audio
    bytes received from audio source to the StreamingAnalyzeContentRequest
    Reference: https://cloud.google.com/python/docs/reference/dialogflow/latest/google.cloud.dialogflow_v2.services.participants.ParticipantsAsyncClient"""

    def __init__(self, rate, chunk_size):
        self._rate = rate
        self.chunk_size = chunk_size
        self._num_channels = 1
        self._buff = queue.Queue()
        self.is_final = False
        self.closed = False
        self.terminate = False
        # Count the number of times the stream analyze content restarts.
        self.restart_counter = 0
        self.last_start_time = 0
        self.terminate = False
        self.total_input_audio_time = 0
        # Time end of the last is_final in millisecond since last_start_time.
        self.is_final_offset = 0
        # Time end of the interim result speech end offset in second
        self.speech_end_offset = 0
        # Save the audio chunks generated from the start of the audio stream for
        # replay after restart.
        # stt model
        self.stt_model = "chirp_3"
        self.audio_input_chunks = []
        self.new_stream = True
        # Only MULAW audio encodings are currently supported in Audiohook
        # Monitor
        self.audio_encoding = dialogflow.AudioEncoding.AUDIO_ENCODING_MULAW
        self.buffer_byte_size = 0
        self._lock = threading.Lock()

    def fill_buffer(self, in_data, *args, **kwargs):
        """Append audio data to buffer if not full"""

        with self._lock:
            self._buff.put(in_data)
            self.buffer_byte_size += len(in_data)
            # Drop excessive audio if buffer exceeds 10 seconds (approx 80KB for 8kHz MULAW)
            max_buffer_bytes = MAX_BUFFER_SECONDS * self._rate
        
            while self.buffer_byte_size > max_buffer_bytes:       
                try:
                    dropped_chunk = self._buff.get_nowait()
                    if dropped_chunk:
                        self.buffer_byte_size -= len(dropped_chunk)
                except queue.Empty:
                    logging.debug("Buffer size: %s, max buffer size: %s", self.buffer_byte_size, max_buffer_bytes)
                    break
    def define_audio_config(
            self,
            conversation_profile: dialogflow.ConversationProfile):
        """The Audiohook client will currently only offer PCMU.
        Reference:
        https://cloud.google.com/agent-assist/docs/extended-streaming
        https://developer.genesys.cloud/devapps/audiohook/session-walkthrough#audio-streaming
        """

        language_code = conversation_profile.stt_config.language_code or "en-US"
        self.stt_model = conversation_profile.stt_config.model or "chirp_3"
        audio_input_config = dialogflow.InputAudioConfig(
            audio_encoding=self.audio_encoding,
            sample_rate_hertz=self._rate,
            language_code=language_code,
            model=self.stt_model,
            model_variant="USE_ENHANCED",
            enable_automatic_punctuation=True)
        logging.debug("Input audio config %s ", audio_input_config)
        return audio_input_config

    def generator(self):
        """Stream Audio from Genesys Audiohook Monitor to API and to local buffer"""
        # Handle restart.
        logging.debug("Restart generator")
        self.restart_counter += 1
        # After the restart of the streaming, set is_final to False
        # to resume populating audio data
        self.is_final = False
        total_processed_time = self.last_start_time + self.is_final_offset
        # ApproximatesBytes = Rate(Sample per Second) * Duration(Seconds) *  BitRate(Bits per Sample) / 8
        # MULAW audio format is 8bit depth, 8000HZ then convert bits to bytes by
        # dividing 8
        # reference https://en.wikipedia.org/wiki/G.711
        processed_bytes_length = (
            int(total_processed_time * self._rate) / 1000
        )
        logging.debug(
            "last start time is %s, is final offset: %s, total processed time %s",
            self.last_start_time,
            self.is_final_offset,
            total_processed_time)
        self.last_start_time = total_processed_time
        # Send out bytes stored in self.audio_input_chunks that is after the
        # processed_bytes_length.
        if processed_bytes_length != 0 and self.stt_model != "chirp_3":
            audio_bytes = b"".join(self.audio_input_chunks)
            # Lookback for unprocessed audio data.
            # ApproximatesBytes = Rate(Sample per Second) * Duration(Seconds) *  BitRate(Bits per Sample) / 8
            # reference https://en.wikipedia.org/wiki/G.711
            need_to_process_length = min(
                int(len(audio_bytes) - processed_bytes_length),
                int(config.max_lookback * self._rate),
            )
            # Note that you need to explicitly use `int` type for
            # substring.
            need_to_process_bytes = audio_bytes[(-1)
                                                * need_to_process_length:]
            logging.debug(
                "Sending need to process bytes length %s, total audio byte length %s, processed byte length %s ",
                len(need_to_process_bytes),
                len(audio_bytes),
                processed_bytes_length)
            try:
                yield need_to_process_bytes
            except GeneratorExit as e:
                logging.debug(
                    "Generator exit from the need to process step %s", e)
                return
        try:
            while not self.closed:
                if self.is_final:
                    # Check if the stream has been running for more than 90 seconds
                    if self.speech_end_offset > SINGLE_STREAM_MAX_DURATION:
                        logging.info("Stream running for > 90s (%s ms), closing current stream.", self.speech_end_offset)
                        break
                data = []
                # Use a blocking get() to ensure there's at least one chunk of
                # data, and stop iteration if the chunk is None, indicating the
                # end of the audio stream.
                try:
                    chunk = self._buff.get(block=True, timeout=0.5)
                    with self._lock:
                        self.buffer_byte_size -= len(chunk)
                except queue.Empty:
                    logging.debug(
                        "queue is empty break the loop and stop generator")
                    break
                if chunk is None:
                    logging.debug(
                        "chunk is none half close the stream by stopping generates requests")
                    return
                data.append(chunk)
                # Now try to the rest of chunks if there are any left in the
                # _buff.
                while True:
                    try:
                        chunk = self._buff.get(block=False)
                        if chunk is None:
                            logging.debug(
                                "Remaining chunk is none half close the stream")
                            return
                        with self._lock:
                            self.buffer_byte_size -= len(chunk)
                        data.append(chunk)
                    except queue.Empty:
                        # queue is empty quitting the loop
                        break
                self.audio_input_chunks.extend(data)

                if data:
                    yield b"".join(data)
        except GeneratorExit as e:
            logging.debug("Generator exit after is_final set to true %s", e)
            return
        logging.debug("Stop generator")
