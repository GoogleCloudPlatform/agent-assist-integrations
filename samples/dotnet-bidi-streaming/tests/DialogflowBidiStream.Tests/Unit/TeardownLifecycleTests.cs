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
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

/// <summary>
/// Unit tests for clean shutdown, teardown ordering, and disposal idempotency.
/// Ensures no unhandled task exceptions or socket/buffer leaks occur when closing streams.
/// </summary>
[Trait("Category", "Unit")]
public class TeardownLifecycleTests
{
    private readonly DialogflowStreamingHarness _harness = new();
    private readonly IOptions<DialogflowStreamingOptions> _options = Options.Create(new DialogflowStreamingOptions
    {
        ProjectId = "teardown-proj",
        LocationId = "global"
    });

    [Fact]
    public async Task StopAsync_DuringActiveStreaming_FlushesAndCompletesCleanly()
    {
        var (writer, reader, _) = _harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-stop-active",
            "agent-1",
            "HUMAN_AGENT",
            _options,
            NullLogger.Instance);

        var finalState = StreamSessionState.Initialized;
        session.StateChanged += (sender, e) => finalState = e.State;

        session.Start();
        Assert.True(await writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        // Continuously push audio in background task
        using var pushCts = new CancellationTokenSource();
        var pushTask = Task.Run(async () =>
        {
            byte[] frame = new byte[160];
            while (!pushCts.IsCancellationRequested)
            {
                session.PushAudio(frame);
                await Task.Delay(5);
            }
        });

        // Let some audio stream
        await Task.Delay(50);

        // Initiate graceful stop while push is still running
        await session.StopAsync();
        pushCts.Cancel();
        await pushTask;

        // Verify request stream was cleanly completed
        Assert.True(writer.IsCompleted);

        // Subsequent pushes should be safely ignored without throwing
        session.PushAudio(new byte[160]);

        Assert.Equal(StreamSessionState.Completed, finalState);
    }

    [Fact]
    public async Task DisposeAsync_IsIdempotent_AndCanBeInvokedMultipleTimes()
    {
        var (writer, reader, _) = _harness.EnqueueStream();

        var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-idempotent-dispose",
            "agent-2",
            "HUMAN_AGENT",
            _options,
            NullLogger.Instance);

        session.Start();
        Assert.True(await writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        await session.DisposeAsync();
        await session.DisposeAsync(); // Second call must not throw ObjectDisposedException
    }
}
