// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using DialogflowBidiStream.Buffers;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

/// <summary>
/// Precision tests for circular ring buffer lookback audio slicing math.
/// Validates byte-accurate extraction of unacknowledged trailing audio across stream rotations.
/// </summary>
[Trait("Category", "Unit")]
public class LookbackBufferMathTests
{
    [Fact]
    public void ExtractLookbackAudio_Mulaw8kHz_AccuratelySlicesTrailingAudio()
    {
        // 8000 Hz, 1 byte/sample (G.711 Mulaw), 3.0s ring buffer capacity (24,000 bytes)
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 3.0, sampleRateHertz: 8000, bytesPerSample: 1);

        // Total written: 2.8 seconds of audio = 22,400 bytes
        int totalBytes = (int)(2.8 * 8000);
        byte[] audio = new byte[totalBytes];
        for (int i = 0; i < totalBytes; i++)
        {
            audio[i] = (byte)(i % 251); // Prime modulo to ensure non-repeating pattern
        }
        buffer.Write(audio);

        // Speech ended at t = 2.0s (16,000 bytes)
        // Trailing unacknowledged audio is from t = 2.0s to 2.8s -> 0.8s (6,400 bytes)
        var lastFinalOffset = TimeSpan.FromSeconds(2.0);
        byte[] lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: lastFinalOffset,
            sampleRateHertz: 8000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.5);

        int expectedLength = (int)(0.8 * 8000); // 6,400 bytes
        Assert.Equal(expectedLength, lookback.Length);

        // Verify exact byte alignment: should match the tail of the audio from 16,000 to 22,400
        int startOffset = (int)(2.0 * 8000);
        for (int i = 0; i < expectedLength; i++)
        {
            Assert.Equal(audio[startOffset + i], lookback[i]);
        }
    }

    [Fact]
    public void ExtractLookbackAudio_CapsAtMaxLookbackSeconds_WhenDeltaExceedsWindow()
    {
        // 8000 Hz, 1 byte/sample, 3.0s ring buffer
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 3.0, sampleRateHertz: 8000, bytesPerSample: 1);

        // Total written: 2.8s = 22,400 bytes
        int totalBytes = (int)(2.8 * 8000);
        byte[] audio = new byte[totalBytes];
        for (int i = 0; i < totalBytes; i++)
        {
            audio[i] = (byte)(i % 256);
        }
        buffer.Write(audio);

        // Speech ended at t = 0.5s -> delta is 2.3s
        // Max lookback window is 1.5s (12,000 bytes)
        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.FromSeconds(0.5),
            sampleRateHertz: 8000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.5);

        int expectedLength = (int)(1.5 * 8000); // 12,000 bytes
        Assert.Equal(expectedLength, lookback.Length);

        // Verify it extracts the most recent 12,000 bytes (from index 10,400 to 22,400)
        int expectedStart = totalBytes - expectedLength;
        for (int i = 0; i < expectedLength; i++)
        {
            Assert.Equal(audio[expectedStart + i], lookback[i]);
        }
    }

    [Fact]
    public void ExtractLookbackAudio_Pcm16kHz_CalculatesTwoBytesPerSampleAccurately()
    {
        // 16000 Hz, 2 bytes/sample (16-bit Linear PCM) = 32,000 bytes/sec
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 3.0, sampleRateHertz: 16000, bytesPerSample: 2);

        // Write 2.0 seconds of 16kHz PCM = 64,000 bytes
        int totalBytes = 2 * 16000 * 2;
        byte[] audio = new byte[totalBytes];
        for (int i = 0; i < totalBytes; i++)
        {
            audio[i] = (byte)(i % 256);
        }
        buffer.Write(audio);

        // Speech ended at t = 1.25s -> delta is 0.75s
        // Lookback bytes = 0.75s * 16000 * 2 = 24,000 bytes
        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.FromSeconds(1.25),
            sampleRateHertz: 16000,
            bytesPerSample: 2,
            maxLookbackSeconds: 1.5);

        int expectedLength = (int)(0.75 * 16000 * 2); // 24,000 bytes
        Assert.Equal(expectedLength, lookback.Length);

        int expectedStart = (int)(1.25 * 16000 * 2);
        for (int i = 0; i < expectedLength; i++)
        {
            Assert.Equal(audio[expectedStart + i], lookback[i]);
        }
    }
}
