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

using Google.Cloud.Dialogflow.V2Beta1;
using Google.Protobuf.WellKnownTypes;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Integration;

[Trait("Category", "Integration")]
public class StreamRotationIntegrationTests
{
    [Fact]
    public async Task Session_RotatesAtUtteranceBoundary_AndPrependLookbackAudio()
    {
        var harness = new DialogflowStreamingHarness();
        var (stream1Writer, stream1Reader, _) = harness.EnqueueStream();
        var (stream2Writer, stream2Reader, _) = harness.EnqueueStream();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "global",
            DefaultSampleRateHertz = 8000,
            DefaultAudioEncoding = AudioEncoding.Mulaw,
            MaxLookbackSeconds = 1.0,
            RestartThreshold = TimeSpan.FromMilliseconds(50), // Low threshold for fast testing
            MaxStreamLifetime = TimeSpan.FromSeconds(5)
        });

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-rotation-test",
            "agent-1",
            "HUMAN_AGENT",
            options,
            NullLogger.Instance);

        var states = new List<StreamSessionState>();
        session.StateChanged += (sender, e) => states.Add(e.State);

        session.Start();

        // 1. Wait for stream #1 to connect and send config
        Assert.True(await stream1Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));
        Assert.Equal(1, session.RotationCount);

        // 2. Stream audio past the 50ms restart threshold
        byte[] audioChunk = new byte[800]; // 100ms of 8kHz audio
        Array.Fill<byte>(audioChunk, 0x55);
        session.PushAudio(audioChunk);
        await Task.Delay(70);

        // 3. Emit Interim transcript -> Should NOT rotate yet!
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "I am speaking...",
                IsFinal = false
            }
        });

        await Task.Delay(50);
        Assert.Equal(1, session.RotationCount);
        Assert.DoesNotContain(StreamSessionState.Rotating, states);

        // 4. Emit Final transcript with speech offset -> triggers safe rotation!
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "I am speaking now.",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromMilliseconds(50))
            }
        });

        // 5. Wait for stream #2 to be established
        Assert.True(await stream2Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)), "Stream #2 did not receive initial config");

        // Verify rotation state transitions
        Assert.Contains(StreamSessionState.Rotating, states);
        Assert.Contains(StreamSessionState.Rotated, states);
        Assert.Equal(2, session.RotationCount);

        // 6. Verify Stream #2 got lookback audio prepended!
        // First message is Config, second message should be Lookback Audio
        Assert.True(await stream2Writer.WaitForMessageCountAsync(2, TimeSpan.FromSeconds(2)), "Stream #2 did not receive lookback audio");
        var lookbackMsg = stream2Writer.WrittenMessages[1];
        Assert.NotNull(lookbackMsg.Input);
        Assert.NotEmpty(lookbackMsg.Input.Audio);

        await session.StopAsync();
    }

    [Fact]
    public async Task Session_ForcesRotation_WhenMaxStreamLifetimeApproachedWithoutBoundary()
    {
        var harness = new DialogflowStreamingHarness();
        var (stream1Writer, stream1Reader, _) = harness.EnqueueStream();
        var (stream2Writer, stream2Reader, _) = harness.EnqueueStream();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "global",
            DefaultSampleRateHertz = 8000,
            DefaultAudioEncoding = AudioEncoding.Mulaw,
            RestartThreshold = TimeSpan.FromMilliseconds(50),
            MaxStreamLifetime = TimeSpan.FromMilliseconds(100) // Fallback threshold
        });

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-fallback-test",
            "agent-2",
            "HUMAN_AGENT",
            options,
            NullLogger.Instance);

        var states = new List<StreamSessionState>();
        session.StateChanged += (sender, e) => states.Add(e.State);

        session.Start();

        Assert.True(await stream1Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        // Continuously send interim speech (no isFinal event)
        for (int i = 0; i < 5; i++)
        {
            await Task.Delay(30);
            stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
            {
                RecognitionResult = new StreamingRecognitionResult
                {
                    Transcript = "Continuous monologue without pause...",
                    IsFinal = false
                }
            });
        }

        // Wait for forced rotation to occur
        Assert.True(await stream2Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(3)), "Stream #2 was not opened by forced rotation");
        Assert.Equal(2, session.RotationCount);
        Assert.Contains(StreamSessionState.Rotating, states);

        await session.StopAsync();
    }
}
