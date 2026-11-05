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
using Moq;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class DialogflowConversationManagerTests
{
    private readonly Mock<ConversationsClient> _mockConversationsClient = new();
    private readonly Mock<ConversationProfilesClient> _mockProfilesClient = new();
    private readonly Mock<ParticipantsClient> _mockParticipantsClient = new();

    private DialogflowConversationManager CreateManager(DialogflowStreamingOptions? options = null)
    {
        var opts = Options.Create(options ?? new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "global",
            ConversationProfileName = "projects/test-project/conversationProfiles/default-profile"
        });

        return new DialogflowConversationManager(
            _mockConversationsClient.Object,
            _mockProfilesClient.Object,
            _mockParticipantsClient.Object,
            opts,
            NullLogger<DialogflowConversationManager>.Instance);
    }

    [Fact]
    public async Task GetOrCreateConversationAsync_ReturnsExisting_WhenFound()
    {
        var manager = CreateManager();
        var existingConversation = new Conversation
        {
            Name = "projects/test-project/conversations/call-100",
            LifecycleState = Conversation.Types.LifecycleState.InProgress
        };

        _mockConversationsClient
            .Setup(c => c.GetConversationAsync(
                It.Is<GetConversationRequest>(r => r.Name == "projects/test-project/conversations/call-100"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(existingConversation);

        var result = await manager.GetOrCreateConversationAsync("call-100");

        Assert.NotNull(result);
        Assert.Equal("projects/test-project/conversations/call-100", result.Name);
        _mockConversationsClient.Verify(c => c.CreateConversationAsync(It.IsAny<CreateConversationRequest>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task GetOrCreateConversationAsync_CreatesNew_WhenNotFound()
    {
        var manager = CreateManager();
        var createdConversation = new Conversation
        {
            Name = "projects/test-project/conversations/call-200",
            LifecycleState = Conversation.Types.LifecycleState.InProgress
        };

        _mockConversationsClient
            .Setup(c => c.GetConversationAsync(
                It.Is<GetConversationRequest>(r => r.Name == "projects/test-project/conversations/call-200"),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.NotFound, "Not Found")));

        _mockConversationsClient
            .Setup(c => c.CreateConversationAsync(
                It.Is<CreateConversationRequest>(r =>
                    r.Parent == "projects/test-project" &&
                    r.ConversationId == "call-200" &&
                    r.Conversation.ConversationProfile == "projects/test-project/conversationProfiles/default-profile"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(createdConversation);

        var result = await manager.GetOrCreateConversationAsync("call-200");

        Assert.NotNull(result);
        Assert.Equal("projects/test-project/conversations/call-200", result.Name);
    }

    [Fact]
    public async Task GetOrCreateConversationAsync_HandlesAlreadyExistsRaceCondition()
    {
        var manager = CreateManager();
        var existingConversation = new Conversation
        {
            Name = "projects/test-project/conversations/call-300",
            LifecycleState = Conversation.Types.LifecycleState.InProgress
        };

        // First GET throws NotFound
        // Second GET (after AlreadyExists) returns existing
        var getSeq = _mockConversationsClient
            .SetupSequence(c => c.GetConversationAsync(
                It.Is<GetConversationRequest>(r => r.Name == "projects/test-project/conversations/call-300"),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.NotFound, "Not Found")))
            .ReturnsAsync(existingConversation);

        _mockConversationsClient
            .Setup(c => c.CreateConversationAsync(
                It.IsAny<CreateConversationRequest>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.AlreadyExists, "Already Exists")));

        var result = await manager.GetOrCreateConversationAsync("call-300");

        Assert.NotNull(result);
        Assert.Equal("projects/test-project/conversations/call-300", result.Name);
    }

    [Fact]
    public async Task GetOrCreateConversationAsync_FormatsRegionalPathsCorrectly()
    {
        var options = new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "us-central1",
            ConversationProfileName = "projects/test-project/locations/us-central1/conversationProfiles/cp-reg"
        };
        var manager = CreateManager(options);

        _mockConversationsClient
            .Setup(c => c.GetConversationAsync(
                It.Is<GetConversationRequest>(r => r.Name == "projects/test-project/locations/us-central1/conversations/call-reg"),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.NotFound, "Not Found")));

        _mockConversationsClient
            .Setup(c => c.CreateConversationAsync(
                It.Is<CreateConversationRequest>(r =>
                    r.Parent == "projects/test-project/locations/us-central1" &&
                    r.ConversationId == "call-reg"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Conversation { Name = "projects/test-project/locations/us-central1/conversations/call-reg" });

        var result = await manager.GetOrCreateConversationAsync("call-reg");

        Assert.Equal("projects/test-project/locations/us-central1/conversations/call-reg", result.Name);
    }

    [Fact]
    public async Task GetOrCreateConversationAsync_Throws_WhenProfileMissing()
    {
        var options = new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "global",
            ConversationProfileName = ""
        };
        var manager = CreateManager(options);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            manager.GetOrCreateConversationAsync("call-missing-profile"));
    }

    [Fact]
    public async Task CreateParticipantAsync_CreatesHumanAgentCorrectly()
    {
        var manager = CreateManager();
        var expectedParticipant = new Participant
        {
            Name = "projects/test-project/conversations/call-1/participants/p-agent",
            Role = Participant.Types.Role.HumanAgent
        };

        _mockParticipantsClient
            .Setup(p => p.CreateParticipantAsync(
                It.Is<CreateParticipantRequest>(r =>
                    r.Parent == "projects/test-project/conversations/call-1" &&
                    r.Participant.Role == Participant.Types.Role.HumanAgent),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedParticipant);

        var result = await manager.CreateParticipantAsync("call-1", Participant.Types.Role.HumanAgent);

        Assert.NotNull(result);
        Assert.Equal(Participant.Types.Role.HumanAgent, result.Role);
        Assert.Equal("projects/test-project/conversations/call-1/participants/p-agent", result.Name);
    }

    [Fact]
    public async Task CreateParticipantAsync_CreatesEndUserInRegionalLocation()
    {
        var options = new DialogflowStreamingOptions
        {
            ProjectId = "test-project",
            LocationId = "europe-west1",
            ConversationProfileName = "cp-eur"
        };
        var manager = CreateManager(options);

        _mockParticipantsClient
            .Setup(p => p.CreateParticipantAsync(
                It.Is<CreateParticipantRequest>(r =>
                    r.Parent == "projects/test-project/locations/europe-west1/conversations/call-2" &&
                    r.Participant.Role == Participant.Types.Role.EndUser),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Participant
            {
                Name = "projects/test-project/locations/europe-west1/conversations/call-2/participants/p-user",
                Role = Participant.Types.Role.EndUser
            });

        var result = await manager.CreateParticipantAsync("call-2", Participant.Types.Role.EndUser);

        Assert.Equal(Participant.Types.Role.EndUser, result.Role);
    }

    [Fact]
    public async Task CompleteConversationAsync_ReturnsCompletedConversation_OnSuccess()
    {
        var manager = CreateManager();
        var completedConversation = new Conversation
        {
            Name = "projects/test-project/conversations/call-done",
            LifecycleState = Conversation.Types.LifecycleState.Completed
        };

        _mockConversationsClient
            .Setup(c => c.CompleteConversationAsync(
                It.Is<CompleteConversationRequest>(r => r.Name == "projects/test-project/conversations/call-done"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(completedConversation);

        var result = await manager.CompleteConversationAsync("call-done");

        Assert.NotNull(result);
        Assert.Equal(Conversation.Types.LifecycleState.Completed, result.LifecycleState);
    }

    [Fact]
    public async Task CompleteConversationAsync_ReturnsNull_WhenNotFound()
    {
        var manager = CreateManager();

        _mockConversationsClient
            .Setup(c => c.CompleteConversationAsync(
                It.IsAny<CompleteConversationRequest>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.NotFound, "Conversation not found")));

        var result = await manager.CompleteConversationAsync("call-notfound");

        Assert.Null(result);
    }

    [Fact]
    public async Task CompleteConversationAsync_ReturnsNull_WhenAlreadyCompletedOrFailedPrecondition()
    {
        var manager = CreateManager();

        _mockConversationsClient
            .Setup(c => c.CompleteConversationAsync(
                It.IsAny<CompleteConversationRequest>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.FailedPrecondition, "Conversation already completed")));

        var result = await manager.CompleteConversationAsync("call-already-closed");

        Assert.Null(result);
    }

    [Fact]
    public async Task GetConversationProfileAsync_ReturnsProfile_WhenFound()
    {
        var manager = CreateManager();
        var expectedProfile = new ConversationProfile
        {
            Name = "projects/test-project/conversationProfiles/cp-main"
        };

        _mockProfilesClient
            .Setup(p => p.GetConversationProfileAsync(
                It.Is<GetConversationProfileRequest>(r => r.Name == "projects/test-project/conversationProfiles/cp-main"),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedProfile);

        var result = await manager.GetConversationProfileAsync("projects/test-project/conversationProfiles/cp-main");

        Assert.NotNull(result);
        Assert.Equal("projects/test-project/conversationProfiles/cp-main", result.Name);
    }

    [Fact]
    public async Task GetConversationProfileAsync_ReturnsNull_OnException()
    {
        var manager = CreateManager();

        _mockProfilesClient
            .Setup(p => p.GetConversationProfileAsync(
                It.IsAny<GetConversationProfileRequest>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(new RpcException(new Status(StatusCode.PermissionDenied, "Access denied")));

        var result = await manager.GetConversationProfileAsync("projects/test-project/conversationProfiles/cp-inaccessible");

        Assert.Null(result);
    }
}
