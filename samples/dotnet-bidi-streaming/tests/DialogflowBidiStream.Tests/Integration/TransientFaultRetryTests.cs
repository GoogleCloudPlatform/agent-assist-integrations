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
using Grpc.Core;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Integration;

[Trait("Category", "Integration")]
public class TransientFaultRetryTests
{
    private readonly IOptions<DialogflowStreamingOptions> _defaultOptions = Options.Create(new DialogflowStreamingOptions
    {
        ProjectId = "test-project",
        LocationId = "global"
    });

    [Fact]
    public async Task Session_RecoversFromTransientRpcException_AndReplacesStream()
    {
        var harness = new DialogflowStreamingHarness();
        var (stream1Writer, stream1Reader, _) = harness.EnqueueStream();
        var (stream2Writer, stream2Reader, _) = harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-retry-test",
            "agent-retry",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        var states = new List<StreamSessionState>();
        session.StateChanged += (sender, e) => states.Add(e.State);

        session.Start();

        // Wait for Stream #1 config
        Assert.True(await stream1Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        // Simulate transient network error on Stream #1
        stream1Reader.Fail(new RpcException(new Status(StatusCode.Unavailable, "Transient network drop")));

        // Wait for Stream #2 to be established
        Assert.True(await stream2Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(3)), "Stream #2 was not established after transient failure");

        // Verify Retrying state occurred
        Assert.Contains(StreamSessionState.Retrying, states);
        Assert.Equal(2, session.RotationCount);

        // Verify audio can be pushed and received on Stream #2
        byte[] chunk = new byte[] { 0x12, 0x34 };
        session.PushAudio(chunk);

        Assert.True(await stream2Writer.WaitForMessageCountAsync(2, TimeSpan.FromSeconds(2)));

        await session.StopAsync();
    }

    [Fact]
    public async Task Session_TransitionsToFaulted_OnFatalRpcException()
    {
        var harness = new DialogflowStreamingHarness();
        var (stream1Writer, stream1Reader, _) = harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            harness.MockParticipantsClient.Object,
            "call-fatal-test",
            "agent-fatal",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        var states = new List<StreamSessionState>();
        session.StateChanged += (sender, e) => states.Add(e.State);

        session.Start();

        Assert.True(await stream1Writer.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2)));

        // Simulate non-transient fatal error (e.g. PermissionDenied)
        stream1Reader.Fail(new RpcException(new Status(StatusCode.PermissionDenied, "Invalid credentials")));

        // Wait for worker to stop
        await Task.Delay(200);

        Assert.Contains(StreamSessionState.Faulted, states);
        // Should NOT attempt rotation or retry
        Assert.Equal(1, session.RotationCount);

        await session.StopAsync();
    }
}
