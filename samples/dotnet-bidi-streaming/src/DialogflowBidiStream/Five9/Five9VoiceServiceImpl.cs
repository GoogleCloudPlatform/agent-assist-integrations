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
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;

namespace DialogflowBidiStream.Five9;

/// <summary>
/// Production gRPC Servicer implementing Five9 VoiceStream (voice.proto) to Dialogflow Bidi-SAC bridge.
/// Compatible with Five9 MediaStream specifications and drop-in adaptable for NICE CXone / CCaaS.
/// </summary>
public class Five9VoiceServiceImpl : Voice.VoiceBase
{
    private readonly IDialogflowConversationManager _conversationManager;
    private readonly ParticipantsClient _participantsClient;
    private readonly IOptions<DialogflowStreamingOptions> _options;
    private readonly ILoggerFactory _loggerFactory;
    private readonly ILogger<Five9VoiceServiceImpl> _logger;

    public Five9VoiceServiceImpl(
        IDialogflowConversationManager conversationManager,
        ParticipantsClient participantsClient,
        IOptions<DialogflowStreamingOptions> options,
        ILoggerFactory loggerFactory)
    {
        _conversationManager = conversationManager ?? throw new ArgumentNullException(nameof(conversationManager));
        _participantsClient = participantsClient ?? throw new ArgumentNullException(nameof(participantsClient));
        _options = options ?? throw new ArgumentNullException(nameof(options));
        _loggerFactory = loggerFactory ?? throw new ArgumentNullException(nameof(loggerFactory));
        _logger = loggerFactory.CreateLogger<Five9VoiceServiceImpl>();
    }

    public override async Task StreamingVoice(
        IAsyncStreamReader<StreamingVoiceRequest> requestStream,
        IServerStreamWriter<StreamingVoiceResponse> responseStream,
        ServerCallContext context)
    {
        // 1. Read first message (Must be StreamingConfig)
        if (!await requestStream.MoveNext(context.CancellationToken))
        {
            _logger.LogWarning("StreamingVoice invoked but request stream was immediately empty.");
            return;
        }

        var firstRequest = requestStream.Current;
        if (firstRequest.StreamingRequestCase != StreamingVoiceRequest.StreamingRequestOneofCase.StreamingConfig)
        {
            _logger.LogError("First message was not StreamingConfig. Received: {Case}", firstRequest.StreamingRequestCase);
            await responseStream.WriteAsync(new StreamingVoiceResponse
            {
                Status = new StreamingStatus
                {
                    Code = StreamingStatus.Types.StatusCode.SrvErrorGeneric,
                    Message = "First message must be StreamingConfig."
                }
            });
            return;
        }

        var streamingConfig = firstRequest.StreamingConfig!;
        string rawCallId = streamingConfig.VccCallId;
        string conversationId = long.TryParse(rawCallId, out long numericCallId)
            ? $"five9-{numericCallId:D10}"
            : $"five9-{rawCallId}";

        var participantRole = streamingConfig.CallLeg == StreamingConfig.Types.CallLeg.Customer
            ? Participant.Types.Role.EndUser
            : Participant.Types.Role.HumanAgent;

        string roleName = participantRole == Participant.Types.Role.EndUser ? "END_USER" : "HUMAN_AGENT";
        string logPrefix = $"[{conversationId}][{roleName}]";

        _logger.LogInformation("{Prefix} Incoming voice stream request for CallLeg: {CallLeg}, SampleRate: {Rate}Hz",
            logPrefix, streamingConfig.CallLeg, streamingConfig.VoiceConfig?.SampleRateHertz ?? 8000);

        // 2. Acknowledge client with SRV_REQ_START_STREAMING (1001)
        await responseStream.WriteAsync(new StreamingVoiceResponse
        {
            Status = new StreamingStatus
            {
                Code = StreamingStatus.Types.StatusCode.SrvReqStartStreaming,
                Message = $"{logPrefix}: Start sending audio!"
            }
        });

        // 3. Resolve / Create Dialogflow Conversation
        Conversation conversation;
        try
        {
            conversation = await _conversationManager.GetOrCreateConversationAsync(
                conversationId,
                cancellationToken: context.CancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "{Prefix} Failed to get or create conversation", logPrefix);
            await responseStream.WriteAsync(new StreamingVoiceResponse
            {
                Status = new StreamingStatus
                {
                    Code = StreamingStatus.Types.StatusCode.SrvErrorNoResource,
                    Message = $"{logPrefix}: Conversation creation error: {ex.Message}"
                }
            });
            return;
        }

        // 4. Create Participant
        Participant participant;
        try
        {
            participant = await _conversationManager.CreateParticipantAsync(
                conversationId,
                participantRole,
                cancellationToken: context.CancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "{Prefix} Failed to create participant", logPrefix);
            await responseStream.WriteAsync(new StreamingVoiceResponse
            {
                Status = new StreamingStatus
                {
                    Code = StreamingStatus.Types.StatusCode.SrvErrorNoResource,
                    Message = $"{logPrefix}: Participant creation error: {ex.Message}"
                }
            });
            return;
        }

        string participantId = participant.Name.Split("/participants/").Last();

        // 5. Initialize Bidi-SAC streaming session
        var sessionLogger = _loggerFactory.CreateLogger<DialogflowBidiStreamSession>();
        await using var session = new DialogflowBidiStreamSession(
            _participantsClient,
            conversationId,
            participantId,
            roleName,
            _options,
            sessionLogger);

        // Wire event handlers
        session.TranscriptReceived += (sender, e) =>
        {
            if (e.IsFinal)
            {
                _logger.LogInformation("{Prefix}[Transcript Final] {Transcript} (Offset: {Offset}ms)",
                    logPrefix, e.Transcript, e.SpeechEndOffset.TotalMilliseconds);
            }
        };

        session.SuggestionReceived += (sender, e) =>
        {
            _logger.LogInformation("{Prefix}[Agent Assist Suggestion Received]", logPrefix);
        };

        // Start Dialogflow streaming background loop
        session.Start();

        bool explicitDisconnect = false;
        bool processingError = false;

        // 6. Audio loop: Consume audio packets from Five9 client
        try
        {
            while (await requestStream.MoveNext(context.CancellationToken))
            {
                var msg = requestStream.Current;
                switch (msg.StreamingRequestCase)
                {
                    case StreamingVoiceRequest.StreamingRequestOneofCase.AudioContent:
                        session.PushAudio(msg.AudioContent.Span);
                        break;

                    case StreamingVoiceRequest.StreamingRequestOneofCase.StreamingStatus:
                        var status = msg.StreamingStatus;
                        if (status != null)
                        {
                            _logger.LogInformation("{Prefix} Received status code: {Code} ({Message})",
                                logPrefix, status.Code, status.Message);

                            if (status.Code is StreamingStatus.Types.StatusCode.CltCallEnded
                                or StreamingStatus.Types.StatusCode.CltDisconnect
                                or (StreamingStatus.Types.StatusCode)2001)
                            {
                                _logger.LogInformation("{Prefix} Disconnect status received from client.", logPrefix);
                                explicitDisconnect = true;
                                goto EndAudioLoop;
                            }
                        }
                        break;
                }
            }

        EndAudioLoop:
            _logger.LogInformation("{Prefix} Client finished sending audio frames.", logPrefix);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("{Prefix} Audio request stream cancelled by client.", logPrefix);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "{Prefix} Error consuming audio stream from client", logPrefix);
            processingError = true;
        }

        // 7. Gracefully stop streaming session
        await session.StopAsync();

        // 8. Auto-complete conversation if natural termination or explicit disconnect
        if (!processingError && (explicitDisconnect || _options.Value.AutoCompleteConversationOnDisconnect))
        {
            try
            {
                _logger.LogInformation("{Prefix} Completing conversation {ConversationId}", logPrefix, conversationId);
                await _conversationManager.CompleteConversationAsync(conversationId);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "{Prefix} Error completing conversation during teardown", logPrefix);
            }
        }
    }
}
