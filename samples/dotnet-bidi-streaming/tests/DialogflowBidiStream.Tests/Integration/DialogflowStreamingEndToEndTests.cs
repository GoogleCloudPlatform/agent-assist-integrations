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
using Google.Protobuf.WellKnownTypes;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using DialogflowBidiStream.Five9;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;
using DialogflowBidiStream.Tests.TestDoubles;
using Xunit;

namespace DialogflowBidiStream.Tests.Integration;

[Trait("Category", "Integration")]
public class DialogflowStreamingEndToEndTests
{
    private readonly Mock<IDialogflowConversationManager> _mockConversationManager = new();
    private readonly DialogflowStreamingHarness _harness = new();
    private readonly IOptions<DialogflowStreamingOptions> _options = Options.Create(new DialogflowStreamingOptions
    {
        ProjectId = "integration-project",
        LocationId = "global",
        ConversationProfileName = "projects/integration-project/conversationProfiles/cp-main",
        DefaultSampleRateHertz = 8000,
        DefaultAudioEncoding = AudioEncoding.Mulaw,
        AutoCompleteConversationOnDisconnect = true
    });

    [Fact]
    public async Task FullVoiceStreamLifecycle_ConnectsStreamsAndCleansUpGracefully()
    {
        // 1. Setup conversation & participant mocks
        string expectedConversationId = "five9-0000054321";
        string participantResourceName = $"projects/integration-project/conversations/{expectedConversationId}/participants/part-cust";

        _mockConversationManager
            .Setup(m => m.GetOrCreateConversationAsync(expectedConversationId, It.IsAny<string?>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Conversation
            {
                Name = $"projects/integration-project/conversations/{expectedConversationId}",
                LifecycleState = Conversation.Types.LifecycleState.InProgress
            });

        _mockConversationManager
            .Setup(m => m.CreateParticipantAsync(expectedConversationId, Participant.Types.Role.EndUser, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Participant
            {
                Name = participantResourceName,
                Role = Participant.Types.Role.EndUser
            });

        _mockConversationManager
            .Setup(m => m.CompleteConversationAsync(expectedConversationId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Conversation
            {
                Name = $"projects/integration-project/conversations/{expectedConversationId}",
                LifecycleState = Conversation.Types.LifecycleState.Completed
            });

        // 2. Prepare mock Dialogflow duplex stream
        var (dialogflowWriter, dialogflowReader, _) = _harness.EnqueueStream();

        // 3. Prepare client stream
        var clientRequestReader = new TestAsyncStreamReader<StreamingVoiceRequest>();
        var clientResponseWriter = new TestServerStreamWriter<StreamingVoiceResponse>();
        var serverContext = new TestServerCallContext();

        var service = new Five9VoiceServiceImpl(
            _mockConversationManager.Object,
            _harness.MockParticipantsClient.Object,
            _options,
            NullLoggerFactory.Instance);

        // Run server in background task
        var serviceTask = Task.Run(() => service.StreamingVoice(clientRequestReader, clientResponseWriter, serverContext));

        // 4. Send initial StreamingConfig
        clientRequestReader.Enqueue(new StreamingVoiceRequest
        {
            StreamingConfig = new StreamingConfig
            {
                VccCallId = "54321",
                CallLeg = StreamingConfig.Types.CallLeg.Customer,
                VoiceConfig = new VoiceConfig
                {
                    Encoding = VoiceConfig.Types.AudioEncoding.Mulaw,
                    SampleRateHertz = 8000
                }
            }
        });

        // Verify start streaming status sent to client
        bool ackReceived = await clientResponseWriter.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2));
        Assert.True(ackReceived, "Timed out waiting for start streaming ACK");
        Assert.NotNull(clientResponseWriter.WrittenMessages[0].Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvReqStartStreaming, clientResponseWriter.WrittenMessages[0].Status!.Code);

        // Verify config sent to Dialogflow
        bool configWritten = await dialogflowWriter.WaitForMessageCountAsync(1, TimeSpan.FromSeconds(2));
        Assert.True(configWritten, "Timed out waiting for Dialogflow config request");
        var firstDialogflowMsg = dialogflowWriter.WrittenMessages[0];
        Assert.NotNull(firstDialogflowMsg.Config);
        Assert.Equal(participantResourceName, firstDialogflowMsg.Config.Participant);
        Assert.Equal(AudioEncoding.Mulaw, firstDialogflowMsg.Config.VoiceSessionConfig.InputAudioEncoding);

        // 5. Send Audio Frames from client
        byte[] audioFrame1 = new byte[160];
        Array.Fill<byte>(audioFrame1, 0x11);
        byte[] audioFrame2 = new byte[160];
        Array.Fill<byte>(audioFrame2, 0x22);

        clientRequestReader.Enqueue(new StreamingVoiceRequest
        {
            AudioContent = ByteString.CopyFrom(audioFrame1)
        });
        clientRequestReader.Enqueue(new StreamingVoiceRequest
        {
            AudioContent = ByteString.CopyFrom(audioFrame2)
        });

        // Dialogflow should receive the 2 audio frames (total 3 messages: 1 config + 2 audio)
        bool audioReceivedByDialogflow = await dialogflowWriter.WaitForMessageCountAsync(3, TimeSpan.FromSeconds(2));
        Assert.True(audioReceivedByDialogflow, "Dialogflow did not receive audio chunks");
        Assert.NotNull(dialogflowWriter.WrittenMessages[1].Input);
        Assert.Equal(audioFrame1, dialogflowWriter.WrittenMessages[1].Input.Audio.ToByteArray());
        Assert.NotNull(dialogflowWriter.WrittenMessages[2].Input);
        Assert.Equal(audioFrame2, dialogflowWriter.WrittenMessages[2].Input.Audio.ToByteArray());

        // 6. Dialogflow responds with recognition result
        dialogflowReader.Enqueue(new BidiStreamingAnalyzeContentResponse
        {
            RecognitionResult = new StreamingRecognitionResult
            {
                Transcript = "I need help with my reservation",
                IsFinal = true,
                SpeechEndOffset = Duration.FromTimeSpan(TimeSpan.FromSeconds(2.5))
            }
        });

        // 7. Client sends disconnect status
        clientRequestReader.Enqueue(new StreamingVoiceRequest
        {
            StreamingStatus = new StreamingStatus
            {
                Code = StreamingStatus.Types.StatusCode.CltDisconnect,
                Message = "Call terminated"
            }
        });

        // Dialogflow finishes streaming and closes its response stream (EOF)
        dialogflowReader.Complete();

        // Wait for service to gracefully finish
        var completedTask = await Task.WhenAny(serviceTask, Task.Delay(TimeSpan.FromSeconds(5)));
        Assert.True(completedTask == serviceTask, "StreamingVoice service did not complete within timeout");
        await serviceTask; // Ensure no unhandled exceptions

        // Verify conversation was completed
        _mockConversationManager.Verify(m => m.CompleteConversationAsync(expectedConversationId, It.IsAny<CancellationToken>()), Times.Once);
    }
}
