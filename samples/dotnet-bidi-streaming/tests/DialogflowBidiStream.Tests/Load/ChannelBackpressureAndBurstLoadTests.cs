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

namespace DialogflowBidiStream.Tests.Load;

[Trait("Category", "Load")]
public class ChannelBackpressureAndBurstLoadTests
{
    [Fact]
    public async Task RapidBurstsUnderContention_DrainsCleanly()
    {
        const int parallelProducers = 10;
        const int packetsPerProducer = 300;
        const int totalExpectedPackets = parallelProducers * packetsPerProducer;

        var harness = new DialogflowStreamingHarness();
        var (writer, _, _) = harness.EnqueueStream();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "burst-test-project",
            LocationId = "global"
        });

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-burst-test",
            "agent-burst",
            "HUMAN_AGENT",
            options,
            NullLogger.Instance);

        session.Start();
        Assert.True(await writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        byte[] frame = new byte[160];
        Array.Fill<byte>(frame, 0x33);

        // Multiple parallel tasks calling PushAudio concurrently
        var producerTasks = Enumerable.Range(0, parallelProducers).Select(_ => Task.Run(() =>
        {
            for (int i = 0; i < packetsPerProducer; i++)
            {
                session.PushAudio(frame);
            }
        })).ToArray();

        await Task.WhenAll(producerTasks);

        // Verify all packets (+1 config) arrive at writer without deadlocking
        bool drained = await writer.WaitForMessageCountAsync(totalExpectedPackets + 1, TimeSpan.FromSeconds(8));
        Assert.True(drained, $"Failed to drain burst packets. Expected {totalExpectedPackets + 1}, got {writer.WrittenMessages.Count}");

        await session.StopAsync();
    }

    [Fact]
    public async Task ConcurrentStreamRotations_UnderActiveAudioLoad()
    {
        const int sessionCount = 10;
        var sessions = new List<DialogflowBidiStreamSession>();
        var harnesses = new List<DialogflowStreamingHarness>();
        var stream2Writers = new List<TestClientStreamWriter<BidiStreamingAnalyzeContentRequest>>();
        var stream1Readers = new List<TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse>>();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "multi-rot-project",
            LocationId = "global",
            RestartThreshold = TimeSpan.FromMilliseconds(40),
            MaxStreamLifetime = TimeSpan.FromSeconds(5)
        });

        for (int i = 0; i < sessionCount; i++)
        {
            var harness = new DialogflowStreamingHarness();
            var (s1w, s1r, _) = harness.EnqueueStream();
            var (s2w, s2r, _) = harness.EnqueueStream();

            var session = new DialogflowBidiStreamSession(
                harness.MockParticipantsClient.Object,
                $"call-rot-{i}",
                $"part-{i}",
                "HUMAN_AGENT",
                options,
                NullLogger.Instance);

            harnesses.Add(harness);
            stream1Readers.Add(s1r);
            stream2Writers.Add(s2w);
            sessions.Add(session);

            session.Start();
        }

        // Send audio to all sessions
        byte[] frame = new byte[160];
        foreach (var session in sessions)
        {
            session.PushAudio(frame);
        }

        // Wait past threshold
        await Task.Delay(60);

        // Trigger simultaneous rotation across all sessions via final utterance
        for (int i = 0; i < sessionCount; i++)
        {
            stream1Readers[i].Enqueue(new BidiStreamingAnalyzeContentResponse
            {
                RecognitionResult = new StreamingRecognitionResult
                {
                    Transcript = "Order complete.",
                    IsFinal = true,
                    SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromMilliseconds(40))
                }
            });
        }

        // Verify every session establishes Stream #2 concurrently
        foreach (var s2w in stream2Writers)
        {
            Assert.True(await s2w.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(5)), "Stream #2 did not open during concurrent rotation");
        }

        foreach (var session in sessions)
        {
            Assert.Equal(2, session.RotationCount);
            await session.StopAsync();
            await session.DisposeAsync();
        }
    }
}
