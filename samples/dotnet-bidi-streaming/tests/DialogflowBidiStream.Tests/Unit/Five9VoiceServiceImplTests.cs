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

using Five9.VoiceStream.Grpc;
using Google.Cloud.Dialogflow.V2Beta1;
using Google.Protobuf;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using DialogflowBidiStream.Five9;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class Five9VoiceServiceImplTests
{
    private readonly Mock<IDialogflowConversationManager> _mockConversationManager = new();
    private readonly DialogflowStreamingHarness _harness = new();
    private readonly IOptions<DialogflowStreamingOptions> _defaultOptions = Options.Create(new DialogflowStreamingOptions
    {
        ProjectId = "test-project",
        LocationId = "global",
        ConversationProfileName = "test-profile",
        AutoCompleteConversationOnDisconnect = true
    });

    private Five9VoiceServiceImpl CreateService()
    {
        return new Five9VoiceServiceImpl(
            _mockConversationManager.Object,
            _harness.MockParticipantsClient.Object,
            _defaultOptions,
            NullLoggerFactory.Instance);
    }

    [Fact]
    public async Task StreamingVoice_ImmediatelyEmptyStream_ReturnsGracefully()
    {
        var service = CreateService();
        var requestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        requestReader.Complete(); // Immediately empty

        var responseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var context = new TestServerCallContext();

        await service.StreamingVoice(requestReader, responseWriter, context);

        Assert.Empty(responseWriter.WrittenMessages);
    }

    [Fact]
    public async Task StreamingVoice_FirstMessageNotStreamingConfig_ReturnsSrvErrorGeneric()
    {
        var service = CreateService();
        var requestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        // Send audio instead of config
        requestReader.Enqueue(new StreamingVoiceRequest
        {
            AudioContent = ByteString.CopyFrom(new byte[] { 0x01, 0x02 })
        });

        var responseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var context = new TestServerCallContext();

        await service.StreamingVoice(requestReader, responseWriter, context);

        Assert.Single(responseWriter.WrittenMessages);
        var response = responseWriter.WrittenMessages[0];
        Assert.NotNull(response.Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvErrorGeneric, response.Status.Code);
        Assert.Contains("First message must be StreamingConfig", response.Status.Message);
    }

    [Fact]
    public async Task StreamingVoice_WhenConversationCreationFails_ReturnsSrvErrorNoResource()
    {
        var service = CreateService();
        var requestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        requestReader.Enqueue(new StreamingVoiceRequest
        {
            StreamingConfig = new StreamingConfig
            {
                VccCallId = "12345",
                CallLeg = StreamingConfig.Types.CallLeg.Customer
            }
        });

        _mockConversationManager
            .Setup(m => m.GetOrCreateConversationAsync(It.IsAny<string>(), It.IsAny<string?>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("GCP quota exceeded"));

        var responseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var context = new TestServerCallContext();

        await service.StreamingVoice(requestReader, responseWriter, context);

        Assert.Equal(2, responseWriter.WrittenMessages.Count);
        // First message is start streaming ack
        Assert.NotNull(responseWriter.WrittenMessages[0].Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvReqStartStreaming, responseWriter.WrittenMessages[0].Status!.Code);
        // Second message is error
        Assert.NotNull(responseWriter.WrittenMessages[1].Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvErrorNoResource, responseWriter.WrittenMessages[1].Status!.Code);
    }

    [Fact]
    public async Task StreamingVoice_WhenParticipantCreationFails_ReturnsSrvErrorNoResource()
    {
        var service = CreateService();
        var requestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        requestReader.Enqueue(new StreamingVoiceRequest
        {
            StreamingConfig = new StreamingConfig
            {
                VccCallId = "call-abc",
                CallLeg = StreamingConfig.Types.CallLeg.Agent
            }
        });

        _mockConversationManager
            .Setup(m => m.GetOrCreateConversationAsync("five9-call-abc", It.IsAny<string?>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Conversation { Name = "projects/test-project/conversations/five9-call-abc" });

        _mockConversationManager
            .Setup(m => m.CreateParticipantAsync("five9-call-abc", Participant.Types.Role.HumanAgent, It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("Failed to create participant"));

        var responseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var context = new TestServerCallContext();

        await service.StreamingVoice(requestReader, responseWriter, context);

        Assert.Equal(2, responseWriter.WrittenMessages.Count);
        Assert.NotNull(responseWriter.WrittenMessages[0].Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvReqStartStreaming, responseWriter.WrittenMessages[0].Status!.Code);
        Assert.NotNull(responseWriter.WrittenMessages[1].Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvErrorNoResource, responseWriter.WrittenMessages[1].Status!.Code);
    }

    [Fact]
    public async Task StreamingVoice_FormatsNumericCallIdWithTenDigits()
    {
        var service = CreateService();
        var requestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        requestReader.Enqueue(new StreamingVoiceRequest
        {
            StreamingConfig = new StreamingConfig
            {
                VccCallId = "9876",
                CallLeg = StreamingConfig.Types.CallLeg.Customer
            }
        });

        string capturedConversationId = "";
        Participant.Types.Role capturedRole = Participant.Types.Role.Unspecified;

        _mockConversationManager
            .Setup(m => m.GetOrCreateConversationAsync(It.IsAny<string>(), It.IsAny<string?>(), It.IsAny<CancellationToken>()))
            .Callback<string, string?, CancellationToken>((convId, prof, ct) => capturedConversationId = convId)
            .ReturnsAsync(new Conversation { Name = "projects/test-project/conversations/five9-0000009876" });

        _mockConversationManager
            .Setup(m => m.CreateParticipantAsync(It.IsAny<string>(), It.IsAny<Participant.Types.Role>(), It.IsAny<CancellationToken>()))
            .Callback<string, Participant.Types.Role, CancellationToken>((convId, role, ct) => capturedRole = role)
            .ReturnsAsync(new Participant { Name = "projects/test-project/conversations/five9-0000009876/participants/part-1" });

        // Enqueue stream for Dialogflow
        _harness.EnqueueStream();

        // Complete request reader so stream finishes
        requestReader.Complete();

        var responseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var context = new TestServerCallContext();

        await service.StreamingVoice(requestReader, responseWriter, context);

        Assert.Equal("five9-0000009876", capturedConversationId);
        Assert.Equal(Participant.Types.Role.EndUser, capturedRole);
        _mockConversationManager.Verify(m => m.CompleteConversationAsync("five9-0000009876", It.IsAny<CancellationToken>()), Times.Once);
    }
}
