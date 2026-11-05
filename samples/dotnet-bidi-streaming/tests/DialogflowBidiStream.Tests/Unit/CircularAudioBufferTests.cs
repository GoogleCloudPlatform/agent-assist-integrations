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

[Trait("Category", "Unit")]
public class CircularAudioBufferTests
{
    [Fact]
    public void Write_StoresDataCorrectly()
    {
        // 1 second buffer at 8000 Hz, 1 byte/sample
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 8000, bytesPerSample: 1);

        byte[] chunk = new byte[1000];
        Array.Fill<byte>(chunk, 0x42);

        buffer.Write(chunk);

        Assert.Equal(1000, buffer.Count);
        Assert.Equal(1000, buffer.TotalBytesWritten);
    }

    [Fact]
    public void Write_WrapsAroundWhenCapacityExceeded()
    {
        // 1 second buffer at 1000 Hz, 1 byte/sample -> 1000 bytes capacity
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 1000, bytesPerSample: 1);

        byte[] first800 = new byte[800];
        Array.Fill<byte>(first800, 0x01);
        buffer.Write(first800);

        byte[] next400 = new byte[400];
        Array.Fill<byte>(next400, 0x02);
        buffer.Write(next400);

        Assert.Equal(1000, buffer.Count);
        Assert.Equal(1200, buffer.TotalBytesWritten);

        // Extract lookback of trailing 400 bytes
        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.FromSeconds(0.8), // 800ms offset
            sampleRateHertz: 1000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.0);

        Assert.Equal(400, lookback.Length);
        Assert.All(lookback, b => Assert.Equal(0x02, b));
    }

    [Fact]
    public void ExtractLookbackAudio_ReturnsExpectedSlice_WhenNoFinalUtterance()
    {
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 2.0, sampleRateHertz: 8000, bytesPerSample: 1);

        byte[] audio = new byte[4000]; // 0.5s of audio
        for (int i = 0; i < audio.Length; i++)
        {
            audio[i] = (byte)(i % 256);
        }
        buffer.Write(audio);

        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.Zero,
            sampleRateHertz: 8000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.0);

        // Entire 4000 bytes should be returned since it's within 1.0s (8000 bytes)
        Assert.Equal(4000, lookback.Length);
        Assert.Equal(audio, lookback);
    }

    [Fact]
    public void Write_EmptySpan_IsNoOp()
    {
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 8000, bytesPerSample: 1);
        buffer.Write(ReadOnlySpan<byte>.Empty);

        Assert.Equal(0, buffer.Count);
        Assert.Equal(0, buffer.TotalBytesWritten);
    }

    [Fact]
    public void Write_LargerThanCapacity_KeepsTailOnly()
    {
        // 1000 bytes capacity
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 1000, bytesPerSample: 1);

        byte[] largeChunk = new byte[2500];
        for (int i = 0; i < largeChunk.Length; i++)
        {
            largeChunk[i] = (byte)(i % 256);
        }
        buffer.Write(largeChunk);

        Assert.Equal(1000, buffer.Count);
        Assert.Equal(2500, buffer.TotalBytesWritten);

        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.Zero,
            sampleRateHertz: 1000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.0);

        Assert.Equal(1000, lookback.Length);
        // Should match the last 1000 bytes of largeChunk
        for (int i = 0; i < 1000; i++)
        {
            Assert.Equal(largeChunk[1500 + i], lookback[i]);
        }
    }

    [Fact]
    public void ExtractLookbackAudio_CappedByMaxLookbackSeconds()
    {
        // 3 seconds buffer at 1000 Hz, 1 byte/sample -> 3000 bytes capacity
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 3.0, sampleRateHertz: 1000, bytesPerSample: 1);

        byte[] chunk = new byte[3000];
        Array.Fill<byte>(chunk, 0xAA);
        buffer.Write(chunk);

        // Max lookback requested is 1.0s (1000 bytes), last offset is zero (delta 3.0s)
        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.Zero,
            sampleRateHertz: 1000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.0);

        Assert.Equal(1000, lookback.Length);
    }

    [Fact]
    public void ExtractLookbackAudio_ReturnsEmpty_WhenOffsetBeyondWrittenBytes()
    {
        using var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 1000, bytesPerSample: 1);

        byte[] chunk = new byte[500];
        buffer.Write(chunk);

        // Offset says final utterance was at 600ms, but only 500ms written
        var lookback = buffer.ExtractLookbackAudio(
            lastFinalOffset: TimeSpan.FromMilliseconds(600),
            sampleRateHertz: 1000,
            bytesPerSample: 1,
            maxLookbackSeconds: 1.0);

        Assert.Empty(lookback);
    }

    [Fact]
    public void Dispose_CanBeCalledMultipleTimes()
    {
        var buffer = new CircularAudioBuffer(maxDurationSeconds: 1.0, sampleRateHertz: 8000, bytesPerSample: 1);
        buffer.Dispose();
        buffer.Dispose(); // Should not throw
    }
}
