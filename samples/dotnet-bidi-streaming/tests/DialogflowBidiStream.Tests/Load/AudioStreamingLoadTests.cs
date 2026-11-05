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

using System.Diagnostics;
using Google.Cloud.Dialogflow.V2Beta1;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;
using Xunit.Abstractions;

namespace DialogflowBidiStream.Tests.Load;

[Trait("Category", "Load")]
public class AudioStreamingLoadTests
{
    private readonly ITestOutputHelper _output;

    public AudioStreamingLoadTests(ITestOutputHelper output)
    {
        _output = output;
    }

    [Fact]
    public async Task ConcurrentSessions_SustainHighThroughput_WithoutPacketLoss()
    {
        const int concurrentSessions = 25;
        const int packetsPerSession = 100;
        const int packetSizeBytes = 160; // 20ms G.711 frame at 8kHz

        var sessions = new List<DialogflowBidiStreamSession>();
        var harnesses = new List<DialogflowStreamingHarness>();
        var writers = new List<TestClientStreamWriter<BidiStreamingAnalyzeContentRequest>>();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "load-project",
            LocationId = "global",
            DefaultSampleRateHertz = 8000,
            DefaultAudioEncoding = AudioEncoding.Mulaw
        });

        // Setup concurrent sessions
        for (int i = 0; i < concurrentSessions; i++)
        {
            var harness = new DialogflowStreamingHarness();
            var (writer, _, _) = harness.EnqueueStream();
            var session = new DialogflowBidiStreamSession(
                harness.MockParticipantsClient.Object,
                $"load-call-{i:D4}",
                $"participant-{i}",
                "HUMAN_AGENT",
                options,
                NullLogger.Instance);

            harnesses.Add(harness);
            writers.Add(writer);
            sessions.Add(session);

            session.Start();
        }

        // Wait for all sessions to establish initial stream and write config
        foreach (var writer in writers)
        {
            Assert.True(await writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(3)));
        }

        var sw = Stopwatch.StartNew();
        byte[] audioFrame = new byte[packetSizeBytes];
        Array.Fill<byte>(audioFrame, 0x7E);

        // Stream audio concurrently across all sessions
        var streamingTasks = sessions.Select(async session =>
        {
            for (int p = 0; p < packetsPerSession; p++)
            {
                session.PushAudio(audioFrame);
                await Task.Yield(); // Interleave with other tasks
            }
        });

        await Task.WhenAll(streamingTasks);

        // Verify each session transmitted all audio packets (+1 config message)
        int expectedMessagesPerSession = packetsPerSession + 1;
        foreach (var writer in writers)
        {
            bool completed = await writer.WaitForMessageCountAsync(expectedMessagesPerSession, TimeSpan.FromSeconds(5));
            Assert.True(completed, $"Session did not receive expected {expectedMessagesPerSession} messages (actual: {writer.WrittenMessages.Count})");
        }

        sw.Stop();

        // Teardown
        foreach (var session in sessions)
        {
            await session.StopAsync();
            await session.DisposeAsync();
        }

        long totalBytesSent = (long)concurrentSessions * packetsPerSession * packetSizeBytes;
        double throughputKbPerSec = (totalBytesSent / 1024.0) / sw.Elapsed.TotalSeconds;

        _output.WriteLine($"[Load Test Result] Concurrent Sessions: {concurrentSessions}");
        _output.WriteLine($"[Load Test Result] Total Audio Packets: {concurrentSessions * packetsPerSession}");
        _output.WriteLine($"[Load Test Result] Total Audio Bytes: {totalBytesSent:N0} bytes");
        _output.WriteLine($"[Load Test Result] Elapsed Time: {sw.ElapsedMilliseconds} ms");
        _output.WriteLine($"[Load Test Result] Throughput: {throughputKbPerSec:F2} KB/sec");
    }

    [Fact]
    public async Task HighVolumeStreaming_MaintainsMemoryStability_WithoutGcGen2Pressure()
    {
        const int totalPackets = 10_000;
        const int packetSizeBytes = 160;

        var harness = new DialogflowStreamingHarness();
        var (writer, _, _) = harness.EnqueueStream();

        var options = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "mem-test-project",
            LocationId = "global"
        });

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-mem-test",
            "agent-mem",
            "HUMAN_AGENT",
            options,
            NullLogger.Instance);

        session.Start();
        Assert.True(await writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        // Warmup GC
        GC.Collect(2, GCCollectionMode.Forced, true);
        int initialGen2Collections = GC.CollectionCount(2);
        long initialMemory = GC.GetTotalMemory(true);

        byte[] frame = new byte[packetSizeBytes];
        for (int i = 0; i < totalPackets; i++)
        {
            session.PushAudio(frame);
        }

        // Wait until writer received all packets
        Assert.True(await writer.WaitForMessageCountAsync(totalPackets + 1, TimeSpan.FromSeconds(10)));

        int postGen2Collections = GC.CollectionCount(2);
        long postMemory = GC.GetTotalMemory(false);

        await session.StopAsync();

        int gen2Delta = postGen2Collections - initialGen2Collections;
        long memoryDeltaBytes = postMemory - initialMemory;

        _output.WriteLine($"[GC Stability] Packets: {totalPackets}");
        _output.WriteLine($"[GC Stability] Gen 2 Collections during stream: {gen2Delta}");
        _output.WriteLine($"[GC Stability] Memory Delta: {memoryDeltaBytes / 1024.0:F2} KB");

        // Verify GC Gen 2 collections remain minimal (< 5 under 10k packet burst)
        Assert.True(gen2Delta <= 5, $"Too many Gen 2 GC collections: {gen2Delta}");
    }
}
