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

namespace DialogflowBidiStream.Tests.Unit;

/// <summary>
/// Directly verifies resolution of the Turn-Taking Fallacy (b/573603541).
/// In naive CCaaS connectors, the gRPC stream was erroneously terminated and recreated
/// on every is_final: true transcript, causing transcription drops and Agent Assist disconnection.
/// This test verifies that a single duplex stream remains open across multiple distinct speaker turns.
/// </summary>
[Trait("Category", "Unit")]
public class TurnTakingAntiPatternTests
{
    [Fact]
    public async Task StreamDoesNotRotate_AcrossMultipleFinalUtterances_UnderThreshold()
    {
        var harness = new DialogflowStreamingHarness();
        var (stream1Writer, stream1Reader, _) = harness.EnqueueStream();

        // 14.5 minute threshold
        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "global",
            RestartThreshold = TimeSpan.FromMinutes(14.5),
            MaxStreamLifetime = TimeSpan.FromMinutes(14.83)
        });

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-turn-taking-test",
            "agent-turn",
            "HUMAN_AGENT",
            options,
            NullLogger.Instance);

        var receivedFinalTranscripts = new List<string>();
        session.TranscriptReceived += (sender, e) =>
        {
            if (e.IsFinal)
            {
                receivedFinalTranscripts.Add(e.Transcript);
            }
        };

        session.Start();

        // Wait for initial stream config
        Assert.True(await stream1Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));
        Assert.Equal(1, session.RotationCount);

        // Simulate Turn 1: Caller speaks
        session.PushAudio(new byte[320]); // 40ms of audio
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "Hello, I need help with my flight reservation.",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromSeconds(2.5))
            }
        });

        // Simulate Turn 2: Agent speaks
        session.PushAudio(new byte[320]);
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "Sure, can I have your confirmation code?",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromSeconds(6.1))
            }
        });

        // Simulate Turn 3: Caller replies
        session.PushAudio(new byte[320]);
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "Yes, it is ALPHA-BRAVO-7-9.",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromSeconds(9.8))
            }
        });

        // Simulate Turn 4: Agent confirms
        session.PushAudio(new byte[320]);
        stream1Reader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "Thank you, I found your booking.",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromSeconds(13.2))
            }
        });

        // Wait for all 4 final transcripts to be received
        await Task.Delay(100);

        Assert.Equal(4, receivedFinalTranscripts.Count);
        Assert.Equal("Hello, I need help with my flight reservation.", receivedFinalTranscripts[0]);
        Assert.Equal("Sure, can I have your confirmation code?", receivedFinalTranscripts[1]);
        Assert.Equal("Yes, it is ALPHA-BRAVO-7-9.", receivedFinalTranscripts[2]);
        Assert.Equal("Thank you, I found your booking.", receivedFinalTranscripts[3]);

        // CRITICAL ASSERTION: The stream MUST NOT have rotated!
        // Rotation count remains 1, and RequestStream was NOT closed.
        Assert.Equal(1, session.RotationCount);
        Assert.False(stream1Writer.IsCompleted, "RequestStream was prematurely completed after is_final: true!");
        Assert.Single(harness.CreatedStreams);

        await session.StopAsync();
        Assert.True(stream1Writer.IsCompleted, "RequestStream should be completed only upon session teardown.");
    }
}
