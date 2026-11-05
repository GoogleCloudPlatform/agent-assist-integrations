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
using Moq;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class DialogflowBidiStreamSessionTests
{
    private readonly DialogflowStreamingHarness _harness = new();
    private readonly IOptions<DialogflowStreamingOptions> _defaultOptions = Options.Create(new DialogflowStreamingOptions
    {
        ProjectId = "test-project",
        LocationId = "global"
    });

    [Fact]
    public void Constructor_ValidatesArguments()
    {
        Assert.Throws<ArgumentNullException>(() =>
            new DialogflowBidiStreamSession(null!, "c", "p", "ROLE", _defaultOptions, NullLogger.Instance));

        Assert.Throws<ArgumentNullException>(() =>
            new DialogflowBidiStreamSession(_harness.MockParticipantsClient.Object, null!, "p", "ROLE", _defaultOptions, NullLogger.Instance));

        Assert.Throws<ArgumentNullException>(() =>
            new DialogflowBidiStreamSession(_harness.MockParticipantsClient.Object, "c", null!, "ROLE", _defaultOptions, NullLogger.Instance));

        Assert.Throws<ArgumentNullException>(() =>
            new DialogflowBidiStreamSession(_harness.MockParticipantsClient.Object, "c", "p", "ROLE", null!, NullLogger.Instance));

        Assert.Throws<ArgumentNullException>(() =>
            new DialogflowBidiStreamSession(_harness.MockParticipantsClient.Object, "c", "p", "ROLE", _defaultOptions, null!));
    }

    [Fact]
    public void Constructor_FormatsResourceName_ForGlobalAndRegional()
    {
        var globalSession = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-1",
            "part-1",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        Assert.Equal("projects/test-project/conversations/call-1/participants/part-1", globalSession.ParticipantName);

        var regionalOptions = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "us-east1"
        });

        var regionalSession = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-2",
            "part-2",
            "END_USER",
            regionalOptions,
            NullLogger.Instance);

        Assert.Equal("projects/test-project/locations/us-east1/conversations/call-2/participants/part-2", regionalSession.ParticipantName);
    }

    [Fact]
    public async Task Start_CalledTwice_ThrowsInvalidOperationException()
    {
        _harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-double-start",
            "part-1",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        session.Start();

        Assert.Throws<InvalidOperationException>(() => session.Start());

        await session.StopAsync();
    }

    [Fact]
    public async Task Start_AfterDisposed_ThrowsObjectDisposedException()
    {
        var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-disposed",
            "part-1",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        await session.DisposeAsync();

        Assert.Throws<ObjectDisposedException>(() => session.Start());
    }

    [Fact]
    public async Task PushAudio_HandlesEmptyOrDisposedGracefully()
    {
        _harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-push",
            "part-1",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        // Empty span should not throw
        session.PushAudio(ReadOnlySpan<byte>.Empty);

        // Stop session
        await session.StopAsync();

        // Push after stop should safely no-op
        session.PushAudio(new byte[] { 0x01, 0x02 });
    }

    [Fact]
    public async Task StopAsync_CanBeCalledMultipleTimesSafely()
    {
        _harness.EnqueueStream();

        await using var session = new DialogflowBidiStreamSession(
            _harness.MockParticipantsClient.Object,
            "call-multi-stop",
            "part-1",
            "HUMAN_AGENT",
            _defaultOptions,
            NullLogger.Instance);

        session.Start();

        await session.StopAsync();
        await session.StopAsync(); // Should not throw
    }
}
