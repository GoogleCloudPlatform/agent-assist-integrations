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
"""Unit tests for audio_stream.Stream."""

import os
import secrets
import sys
import unittest

os.environ.setdefault("API_KEY", secrets.token_urlsafe(16))
os.environ.setdefault(
    "CONVERSATION_PROFILE_NAME",
    "projects/test-proj/locations/global/conversationProfiles/test-prof",
)
os.environ.setdefault("GCP_PROJECT_ID", "test-proj")
os.environ.setdefault("UI_CONNECTOR", "https://ui-connector.example")
os.environ.setdefault("REDISHOST", "127.0.0.1")
os.environ.setdefault("REDISPORT", "6379")

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from audio_stream import Stream  # pylint: disable=wrong-import-position


class TestAudioStream(unittest.TestCase):
    """Tests buffered audio batching and stream termination."""

    def test_generator_flushes_queued_chunks_before_none_sentinel(self):
        """Yields buffered audio chunks preceding a None sentinel before closing."""
        stream = Stream(rate=8000, chunk_size=160)
        stream.fill_buffer(b"chunk-1-")
        stream.fill_buffer(b"chunk-2")
        stream._buff.put(None)

        yielded = list(stream.generator())

        self.assertEqual(yielded, [b"chunk-1-chunk-2"])
        self.assertEqual(stream.audio_input_chunks, [b"chunk-1-", b"chunk-2"])
        self.assertTrue(stream.closed)


if __name__ == "__main__":
    unittest.main()
