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

"""Unit tests for the Audiohook session and streaming thread lifecycle.

Run with: python -m unittest test_audiohook_lifecycle.py
"""
import os
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault(
    "CONVERSATION_PROFILE_NAME",
    "projects/test-project/locations/global/conversationProfiles/test")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("UI_CONNECTOR", "https://ui-connector.example.com")
os.environ.setdefault("REDISHOST", "localhost")
os.environ.setdefault("REDISPORT", "6379")

# dialogflow_api resolves default credentials at import time.
with mock.patch("google.auth.default",
                return_value=(mock.Mock(), "test-project")):
    import audiohook_blueprint  # pylint: disable=wrong-import-position
    import dialogflow_api  # pylint: disable=wrong-import-position
    from audio_stream import Stream  # pylint: disable=wrong-import-position

from google.api_core.exceptions import (  # pylint: disable=wrong-import-position
    FailedPrecondition, ResourceExhausted)


def _new_stream():
    return Stream(8000, chunk_size=1600)


def _new_dialogflow_api():
    # Skip __init__, which creates real Dialogflow clients.
    return dialogflow_api.DialogflowAPI.__new__(dialogflow_api.DialogflowAPI)


def _participant():
    participant = mock.Mock()
    participant.role.name = "END_USER"
    return participant


class RepeatedResumeTest(unittest.TestCase):
    """Audiohook can send "paused"/"resumed" several times per session."""

    def setUp(self):
        self.agent_stream = _new_stream()
        self.customer_stream = _new_stream()
        self.start_count = {"agent": 0, "user": 0}

        def run(name, stream):
            self.start_count[name] += 1
            stream.stopped.wait(timeout=5)

        self.state = audiohook_blueprint.OpenConversationState(
            agent_thread=threading.Thread(
                target=run, args=("agent", self.agent_stream), daemon=True),
            user_thread=threading.Thread(
                target=run, args=("user", self.customer_stream), daemon=True),
            conversation_name="projects/p/locations/global/conversations/c",
            is_opened=True)

    def tearDown(self):
        self.agent_stream.stop()
        self.customer_stream.stop()

    def _send(self, message_type):
        return audiohook_blueprint.process_ongoing_conversation_messages(
            {"type": message_type}, mock.Mock(), mock.Mock(),
            self.agent_stream, self.customer_stream, self.state, mock.Mock())

    def test_repeated_resumed_starts_threads_once(self):
        for message_type in ["resumed", "paused", "resumed", "paused",
                             "resumed"]:
            self.assertFalse(self._send(message_type))
        time.sleep(0.1)
        self.assertEqual(self.start_count, {"agent": 1, "user": 1})
        self.assertTrue(self.state.agent_thread.daemon)

    def test_pause_and_resume_toggle_stream_state(self):
        self._send("resumed")
        self.assertFalse(self.customer_stream.closed)
        self.assertTrue(self.customer_stream.active.is_set())
        self._send("paused")
        self.assertTrue(self.customer_stream.closed)
        self.assertFalse(self.customer_stream.active.is_set())
        self._send("resumed")
        self.assertFalse(self.agent_stream.closed)
        self.assertTrue(self.agent_stream.active.is_set())


class ConnectHandlerTest(unittest.TestCase):
    """Exceptions must never escape the flask_sock route."""

    def test_unexpected_error_is_handled_and_streams_are_stopped(self):
        streams = []

        def make_stream(*args, **kwargs):
            stream = Stream(*args, **kwargs)
            streams.append(stream)
            return stream

        with mock.patch.object(audiohook_blueprint, "Stream",
                               side_effect=make_stream), \
                mock.patch.object(audiohook_blueprint,
                                  "handle_audiohook_session",
                                  side_effect=RuntimeError("boom")):
            audiohook_blueprint.run_audiohook_connection(mock.Mock())

        self.assertEqual(len(streams), 2)
        for stream in streams:
            self.assertTrue(stream.terminate)
            self.assertTrue(stream.closed)
            self.assertTrue(stream.stopped.is_set())

    def test_streams_are_stopped_after_normal_close(self):
        streams = []

        def make_stream(*args, **kwargs):
            stream = Stream(*args, **kwargs)
            streams.append(stream)
            return stream

        with mock.patch.object(audiohook_blueprint, "Stream",
                               side_effect=make_stream), \
                mock.patch.object(audiohook_blueprint,
                                  "handle_audiohook_session"):
            audiohook_blueprint.run_audiohook_connection(mock.Mock())

        for stream in streams:
            self.assertTrue(stream.terminate)


class MaintainedStreamingTest(unittest.TestCase):
    """maintained_streaming_analyze_content must not spin or die."""

    def _run_in_thread(self, api, stream):
        thread = threading.Thread(
            target=api.maintained_streaming_analyze_content,
            args=(stream, _participant(), mock.Mock()), daemon=True)
        thread.start()
        return thread

    def test_paused_stream_does_not_busy_spin(self):
        api = _new_dialogflow_api()
        api.streaming_analyze_content = mock.Mock(return_value=True)
        stream = _new_stream()
        stream.pause()
        waits = []
        original_wait = stream.active.wait

        def counting_wait(timeout=None):
            waits.append(timeout)
            return original_wait(timeout)

        stream.active.wait = counting_wait
        thread = self._run_in_thread(api, stream)
        time.sleep(1.0)
        stream.stop()
        thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        api.streaming_analyze_content.assert_not_called()
        # A busy-spin would loop millions of times per second.
        self.assertLess(len(waits), 5)

    def test_resumed_stream_calls_streaming_analyze_content(self):
        api = _new_dialogflow_api()
        stream = _new_stream()
        called = threading.Event()

        def fake_streaming(*_):
            called.set()
            stream.stopped.wait(timeout=0.05)
            return True

        api.streaming_analyze_content = mock.Mock(side_effect=fake_streaming)
        stream.pause()
        thread = self._run_in_thread(api, stream)
        time.sleep(0.2)
        api.streaming_analyze_content.assert_not_called()
        stream.resume()
        self.assertTrue(called.wait(timeout=2))
        stream.stop()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_unexpected_error_does_not_kill_the_thread(self):
        api = _new_dialogflow_api()
        api.streaming_analyze_content = mock.Mock(
            side_effect=[RuntimeError("transient"), True, True, True, True])
        stream = _new_stream()
        stream.resume()
        with mock.patch.object(
                dialogflow_api, "STREAMING_RETRY_INITIAL_BACKOFF_SECONDS",
                0.01):
            thread = self._run_in_thread(api, stream)
            deadline = time.time() + 2
            while (api.streaming_analyze_content.call_count < 3
                   and time.time() < deadline):
                time.sleep(0.01)
            stream.stop()
            thread.join(timeout=2)
        self.assertGreaterEqual(api.streaming_analyze_content.call_count, 3)
        self.assertFalse(thread.is_alive())

    def test_failure_backs_off_and_stop_is_prompt(self):
        api = _new_dialogflow_api()
        api.streaming_analyze_content = mock.Mock(return_value=False)
        stream = _new_stream()
        stream.resume()
        thread = self._run_in_thread(api, stream)
        time.sleep(0.5)
        # Initial backoff is 1s: only the first attempt has happened.
        self.assertEqual(api.streaming_analyze_content.call_count, 1)
        started = time.time()
        stream.stop()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertLess(time.time() - started, 1.0)


class StreamingAnalyzeContentErrorsTest(unittest.TestCase):
    """Quota and precondition errors are retried, not turned into a closed
    stream that only a later "resumed" message could re-open."""

    def _call_with_error(self, error):
        api = _new_dialogflow_api()
        api.participants_client = mock.Mock()
        api.participants_client.streaming_analyze_content.side_effect = error
        api.generator_streaming_analyze_content_request = mock.Mock()
        stream = _new_stream()
        stream.resume()
        result = api.streaming_analyze_content(
            stream, _participant(), mock.Mock())
        return result, stream

    def test_resource_exhausted_is_retried(self):
        result, stream = self._call_with_error(ResourceExhausted("quota"))
        self.assertFalse(result)
        self.assertFalse(stream.closed)

    def test_failed_precondition_is_retried(self):
        result, stream = self._call_with_error(FailedPrecondition("nope"))
        self.assertFalse(result)
        self.assertFalse(stream.closed)

    def test_normal_end_of_stream_returns_true(self):
        api = _new_dialogflow_api()
        api.participants_client = mock.Mock()
        api.participants_client.streaming_analyze_content.return_value = []
        api.generator_streaming_analyze_content_request = mock.Mock()
        stream = _new_stream()
        self.assertTrue(api.streaming_analyze_content(
            stream, _participant(), mock.Mock()))


class LookbackTest(unittest.TestCase):
    """Lookback replays only the unprocessed tail of the audio buffer."""

    def _lookback(self, is_final_offset_ms):
        stream = _new_stream()
        stream.stt_model = "latest_long"
        # 2 seconds of 8 kHz MULAW audio, every byte distinct by position.
        stream.audio_input_chunks = [bytes(range(200)) * 80]
        stream.is_final_offset = is_final_offset_ms
        stream.closed = True  # only exercise the lookback step
        return list(stream.generator())

    def test_replays_unprocessed_tail(self):
        audio = bytes(range(200)) * 80
        # 1.5 s processed -> the last 0.5 s (4000 bytes) is replayed.
        self.assertEqual(self._lookback(1500), [audio[-4000:]])

    def test_nothing_to_replay_when_everything_was_processed(self):
        # Previously audio_bytes[-0:] replayed the whole call buffer.
        self.assertEqual(self._lookback(2000), [])


class StreamStopTest(unittest.TestCase):

    def test_stop_ends_the_audio_generator(self):
        stream = _new_stream()
        stream.resume()
        generator = stream.generator()
        stream.fill_buffer(b"\x00" * 1600)
        self.assertEqual(next(generator), b"\x00" * 1600)
        stream.stop()
        with self.assertRaises(StopIteration):
            next(generator)


if __name__ == "__main__":
    unittest.main()
