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
        # Set while Audiohook is streaming audio (after "resumed"), cleared
        # while it is paused. Streaming threads wait on it instead of
        # busy-spinning while the stream is closed.
        self.active = threading.Event()
        # Set once the Audiohook session has ended.
        self.stopped = threading.Event()

    def resume(self):
        """Re-open the stream after an Audiohook "resumed" message."""
        self.closed = False
        self.active.set()

    def pause(self):
        """Close the current stream after an Audiohook "paused" message."""
        self.closed = True
        self.active.clear()

    def stop(self):
        """Permanently stop the stream when the Audiohook session ends.

        Safe to call more than once. Wakes up any waiting streaming thread;
        the audio generator exits on its next closed check.
        """
        self.closed = True
        self.terminate = True
        self.stopped.set()
        self.active.set()

    def fill_buffer(self, in_data):
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
                    logging.debug("Buffer size: %s, max buffer size: %s", repr(self.buffer_byte_size), repr(max_buffer_bytes))
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

    def _get_lookback_bytes(self, processed_bytes_length):
        """Returns unprocessed lookback audio bytes when restarting non-chirp_3 streams."""
        if processed_bytes_length == 0 or self.stt_model == "chirp_3":
            return b""
        audio_bytes = b"".join(self.audio_input_chunks)
        # Lookback for unprocessed audio data.
        # ApproximatesBytes = Rate(Sample per Second) * Duration(Seconds) *  BitRate(Bits per Sample) / 8
        # reference https://en.wikipedia.org/wiki/G.711
        need_to_process_length = min(
            int(len(audio_bytes) - processed_bytes_length),
            int(config.max_lookback * self._rate),
        )
        if need_to_process_length <= 0:
            return b""
        need_to_process_bytes = audio_bytes[-need_to_process_length:]
        logging.debug(
            "Sending need to process bytes length %s, total audio byte length %s, processed byte length %s ",
            len(need_to_process_bytes),
            len(audio_bytes),
            processed_bytes_length,
        )
        return need_to_process_bytes

    def _drain_queued_chunks(self, first_chunk):
        """Drains remaining queued audio chunks after a blocking get().

        Returns:
            Tuple of (chunks, stop_stream) where stop_stream is True if a None
            sentinel was encountered.
        """
        data = [first_chunk]
        while True:
            try:
                chunk = self._buff.get(block=False)
            except queue.Empty:
                return data, False
            if chunk is None:
                logging.debug("Remaining chunk is none half close the stream")
                return data, True
            with self._lock:
                self.buffer_byte_size -= len(chunk)
            data.append(chunk)

    def _next_audio_batch(self):
        """Fetches the next batch of buffered audio bytes, or None to stop."""
        if self.is_final and self.speech_end_offset > SINGLE_STREAM_MAX_DURATION:
            logging.info(
                "Stream running for > 90s (%s ms), closing current stream.",
                self.speech_end_offset,
            )
            return None
        try:
            chunk = self._buff.get(block=True, timeout=0.5)
        except queue.Empty:
            logging.debug("queue is empty break the loop and stop generator")
            return None
        if chunk is None:
            logging.debug(
                "chunk is none half close the stream by stopping generates requests"
            )
            return None
        with self._lock:
            self.buffer_byte_size -= len(chunk)
        data, stop_stream = self._drain_queued_chunks(chunk)
        self.audio_input_chunks.extend(data)
        if stop_stream:
            self.closed = True
        return b"".join(data)

    def generator(self):
        """Stream Audio from Genesys Audiohook Monitor to API and to local buffer"""
        logging.debug("Restart generator")
        self.restart_counter += 1
        self.is_final = False
        total_processed_time = self.last_start_time + self.is_final_offset
        processed_bytes_length = int(total_processed_time * self._rate) / 1000
        logging.debug(
            "last start time is %s, is final offset: %s, total processed time %s",
            self.last_start_time,
            self.is_final_offset,
            total_processed_time,
        )
        self.last_start_time = total_processed_time
        self.is_final_offset = 0  # already counted; don't add it again next restart

        lookback_bytes = self._get_lookback_bytes(processed_bytes_length)
        if lookback_bytes:
            try:
                yield lookback_bytes
            except GeneratorExit as e:
                logging.debug(
                    "Generator exit from the need to process step %s", e
                )
                return

        try:
            while not self.closed:
                batch = self._next_audio_batch()
                if batch is None:
                    return
                if batch:
                    yield batch
        except GeneratorExit as e:
            logging.debug("Generator exit after is_final set to true %s", e)
            return
        logging.debug("Stop generator")
