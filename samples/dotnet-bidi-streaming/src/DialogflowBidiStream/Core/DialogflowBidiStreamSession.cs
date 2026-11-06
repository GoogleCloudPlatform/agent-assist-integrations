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
using System.Threading.Channels;
using Google.Cloud.Dialogflow.V2Beta1;
using Google.Protobuf;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Buffers;
using DialogflowBidiStream.Models;

namespace DialogflowBidiStream.Core;

/// <summary>
/// Long-lived bidirectional streaming session to Dialogflow BidiStreamingAnalyzeContent.
/// Implements boundary-safe 14.5-minute stream rotation, lookback audio buffer replay,
/// and non-blocking asynchronous audio channeling.
/// </summary>
public sealed class DialogflowBidiStreamSession : IAsyncDisposable
{
    private readonly ParticipantsClient _client;
    private readonly string _conversationId;
    private readonly string _participantId;
    private readonly string _participantRole;
    private readonly string _participantName;
    private readonly DialogflowStreamingOptions _options;
    private readonly ILogger _logger;

    private readonly Channel<ReadOnlyMemory<byte>> _audioChannel;
    private readonly CircularAudioBuffer _audioBuffer;
    private readonly CancellationTokenSource _cts = new();

    private TimeSpan _lastFinalOffset = TimeSpan.Zero;
    private int _streamRotationCounter = 0;
    private Task? _sessionWorkerTask;
    private volatile bool _isDisposed;
    private volatile bool _disconnectRequested;

    public event EventHandler<TranscriptEventArgs>? TranscriptReceived;
    public event EventHandler<SuggestionEventArgs>? SuggestionReceived;
    public event EventHandler<StreamStateEventArgs>? StateChanged;

    public string ConversationId => _conversationId;
    public string ParticipantId => _participantId;
    public string ParticipantRole => _participantRole;
    public string ParticipantName => _participantName;
    public int RotationCount => _streamRotationCounter;

    public DialogflowBidiStreamSession(
        ParticipantsClient client,
        string conversationId,
        string participantId,
        string participantRole,
        IOptions<DialogflowStreamingOptions> options,
        ILogger logger)
    {
        _client = client ?? throw new ArgumentNullException(nameof(client));
        _conversationId = conversationId ?? throw new ArgumentNullException(nameof(conversationId));
        _participantId = participantId ?? throw new ArgumentNullException(nameof(participantId));
        _participantRole = participantRole ?? "HUMAN_AGENT";
        _options = options?.Value ?? throw new ArgumentNullException(nameof(options));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));

        // Format participant resource name: projects/{p}/locations/{l}/conversations/{c}/participants/{part}
        _participantName = _options.LocationId.Equals("global", StringComparison.OrdinalIgnoreCase)
            ? $"projects/{_options.ProjectId}/conversations/{_conversationId}/participants/{_participantId}"
            : $"projects/{_options.ProjectId}/locations/{_options.LocationId}/conversations/{_conversationId}/participants/{_participantId}";

        // High-throughput, non-blocking single-reader channel for audio frames
        _audioChannel = Channel.CreateUnbounded<ReadOnlyMemory<byte>>(new UnboundedChannelOptions
        {
            SingleReader = true,
            SingleWriter = false
        });

        int bytesPerSample = _options.DefaultAudioEncoding == AudioEncoding.Mulaw ? 1 : 2;
        _audioBuffer = new CircularAudioBuffer(
            maxDurationSeconds: 3.0,
            sampleRateHertz: _options.DefaultSampleRateHertz,
            bytesPerSample: bytesPerSample);

        OnStateChanged(StreamSessionState.Initialized, "Session initialized");
    }

    /// <summary>
    /// Starts the background streaming session worker.
    /// </summary>
    public void Start()
    {
        ObjectDisposedException.ThrowIf(_isDisposed, this);

        if (_sessionWorkerTask != null)
        {
            throw new InvalidOperationException("Session is already running.");
        }

        _sessionWorkerTask = Task.Run(RunStreamingLoopAsync);
    }

    /// <summary>
    /// Pushes incoming audio chunk from CCaaS / Five9 / RTP stream into the pipeline.
    /// Thread-safe and non-blocking.
    /// </summary>
    public void PushAudio(ReadOnlySpan<byte> audioChunk)
    {
        if (_isDisposed || _disconnectRequested || audioChunk.IsEmpty)
            return;

        // Copy chunk for channel and update circular buffer
        byte[] copy = audioChunk.ToArray();
        _audioBuffer.Write(copy);
        _audioChannel.Writer.TryWrite(copy);
    }

    /// <summary>
    /// Main session orchestrator loop. Runs across stream rotations until the call terminates.
    /// </summary>
    private async Task RunStreamingLoopAsync()
    {
        OnStateChanged(StreamSessionState.Starting, "Starting streaming loop");

        while (!_cts.Token.IsCancellationRequested && !_disconnectRequested)
        {
            _streamRotationCounter++;
            var sessionTimer = Stopwatch.StartNew();
            bool shouldRotate = false;
            bool isErrorRestart = false;

            _logger.LogInformation("[{ConversationId}][{Role}] Opening Dialogflow stream #{Rotation} (Threshold: {Threshold}m)",
                _conversationId, _participantRole, _streamRotationCounter, _options.RestartThreshold.TotalMinutes);

            AsyncDuplexStreamingCall<BidiStreamingAnalyzeContentRequest, BidiStreamingAnalyzeContentResponse>? duplexCall = null;
            try
            {
                // 1. Establish the Bidi-SAC duplex stream
                duplexCall = _client.GrpcClient.BidiStreamingAnalyzeContent(cancellationToken: _cts.Token);
                OnStateChanged(StreamSessionState.Connected, $"Stream #{_streamRotationCounter} connected");

                // 2. Send initial voice configuration message
                var configRequest = new BidiStreamingAnalyzeContentRequest
                {
                    Config = new BidiStreamingAnalyzeContentRequest.Types.Config
                    {
                        Participant = _participantName,
                        VoiceSessionConfig = new BidiStreamingAnalyzeContentRequest.Types.Config.Types.VoiceSessionConfig
                        {
                            InputAudioEncoding = _options.DefaultAudioEncoding,
                            InputAudioSampleRateHertz = _options.DefaultSampleRateHertz,
                            UseGeminiAsr = true
                        }
                    }
                };

                await duplexCall.RequestStream.WriteAsync(configRequest);

                // 3. Prepend lookback audio from previous stream boundary (if rotating)
                int bytesPerSample = _options.DefaultAudioEncoding == AudioEncoding.Mulaw ? 1 : 2;
                byte[] lookbackPayload = _audioBuffer.ExtractLookbackAudio(
                    _lastFinalOffset,
                    _options.DefaultSampleRateHertz,
                    bytesPerSample,
                    _options.MaxLookbackSeconds);

                if (lookbackPayload.Length > 0)
                {
                    _logger.LogDebug("[{ConversationId}][{Role}] Prepending {Bytes} lookback bytes to stream #{Rotation}",
                        _conversationId, _participantRole, lookbackPayload.Length, _streamRotationCounter);

                    await duplexCall.RequestStream.WriteAsync(new BidiStreamingAnalyzeContentRequest
                    {
                        Input = new BidiStreamingAnalyzeContentRequest.Types.Input
                        {
                            Audio = ByteString.CopyFrom(lookbackPayload)
                        }
                    });
                }

                // CancellationToken for this specific stream incarnation
                using var streamCts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);

                // 4. Writer Task: Reads from Channel and writes into gRPC RequestStream
                var writeTask = Task.Run(async () =>
                {
                    while (await _audioChannel.Reader.WaitToReadAsync(streamCts.Token))
                    {
                        while (_audioChannel.Reader.TryRead(out var chunk))
                        {
                            var audioRequest = new BidiStreamingAnalyzeContentRequest
                            {
                                Input = new BidiStreamingAnalyzeContentRequest.Types.Input
                                {
                                    Audio = ByteString.CopyFrom(chunk.Span)
                                }
                            };

                            await duplexCall.RequestStream.WriteAsync(audioRequest);

                            if (shouldRotate || streamCts.IsCancellationRequested)
                            {
                                return;
                            }
                        }
                    }
                }, streamCts.Token);

                // 5. Reader Task: Reads responses from gRPC ResponseStream
                var readTask = Task.Run(async () =>
                {
                    await foreach (var response in duplexCall.ResponseStream.ReadAllAsync(streamCts.Token))
                    {
                        if (_options.EnableDebugLogging)
                        {
                            _logger.LogDebug("[{ConversationId}][{Role}] Received response: {Case}", _conversationId, _participantRole, response.ResponseCase);
                        }

                        // Handle recognition results (Interim & Final Transcripts)
                        if (response.RecognitionResult != null)
                        {
                            var result = response.RecognitionResult;
                            if (result.IsFinal)
                            {
                                _lastFinalOffset = result.SpeechEndOffset?.ToTimeSpan() ?? TimeSpan.Zero;
                                _logger.LogInformation("[{ConversationId}][{Role}][Final] {Transcript} (Offset: {Offset}ms)",
                                    _conversationId, _participantRole, result.Transcript, _lastFinalOffset.TotalMilliseconds);

                                OnTranscriptReceived(result);

                                // Boundary-Safe Stream Rotation:
                                // Rotate ONLY after a final utterance when crossing the 14.5m threshold!
                                if (sessionTimer.Elapsed > _options.RestartThreshold)
                                {
                                    _logger.LogInformation(
                                        "[{ConversationId}][{Role}] Stream #{Rotation} reached {Elapsed:F1}s (> {Threshold}m). Safe rotation triggered at sentence boundary.",
                                        _conversationId, _participantRole, _streamRotationCounter, sessionTimer.Elapsed.TotalSeconds, _options.RestartThreshold.TotalMinutes);
                                    shouldRotate = true;
                                    break;
                                }
                            }
                            else
                            {
                                if (_options.EnableDebugLogging)
                                {
                                    _logger.LogDebug("[{ConversationId}][{Role}][Interim] {Transcript}",
                                        _conversationId, _participantRole, result.Transcript);
                                }
                                OnTranscriptReceived(result);
                            }
                        }

                        // Forced rotation fallback if caller is silent or long monologue approaches deadline
                        if (sessionTimer.Elapsed > _options.MaxStreamLifetime)
                        {
                            _logger.LogWarning(
                                "[{ConversationId}][{Role}] Stream #{Rotation} approached maximum lifetime {Elapsed:F1}s without final boundary. Triggering rotation.",
                                _conversationId, _participantRole, _streamRotationCounter, sessionTimer.Elapsed.TotalSeconds);
                            shouldRotate = true;
                            break;
                        }

                        // Handle suggestions & Agent Assist events
                        if (response.AnalyzeContentResponse != null)
                        {
                            OnSuggestionReceived(response.AnalyzeContentResponse);
                        }
                    }
                }, streamCts.Token);

                // Wait for either reader or writer to complete or request rotation
                await Task.WhenAny(readTask, writeTask);

                // If reader broke early due to rotation, cancel the stream token to unblock writer
                if (shouldRotate)
                {
                    OnStateChanged(StreamSessionState.Rotating, $"Rotating stream #{_streamRotationCounter}");
                    streamCts.Cancel();
                }

                // Gracefully complete the request stream
                try
                {
                    await duplexCall.RequestStream.CompleteAsync();
                }
                catch (Exception ex)
                {
                    _logger.LogDebug(ex, "[{ConversationId}] RequestStream CompleteAsync suppressed during rotation", _conversationId);
                }

                // Drain reader with graceful timeout to prevent deadlock if remote stream stalls
                try
                {
                    await readTask.WaitAsync(TimeSpan.FromSeconds(2));
                }
                catch (TimeoutException)
                {
                    _logger.LogDebug("[{ConversationId}] Response stream drain timed out after 2s. Cancelling stream.", _conversationId);
                    streamCts.Cancel();
                    try { await readTask; } catch (OperationCanceledException) { }
                }
                catch (OperationCanceledException) { }
            }
            catch (RpcException ex) when (IsTransientRpcException(ex))
            {
                isErrorRestart = true;
                _logger.LogWarning(ex, "[{ConversationId}][{Role}] Transient gRPC error on stream #{Rotation}: {Status}. Reconnecting...",
                    _conversationId, _participantRole, _streamRotationCounter, ex.StatusCode);
                OnStateChanged(StreamSessionState.Retrying, $"Transient retry: {ex.StatusCode}", ex);
                await Task.Delay(250, _cts.Token); // Brief jitter backoff
            }
            catch (OperationCanceledException)
            {
                _logger.LogInformation("[{ConversationId}][{Role}] Stream #{Rotation} cancelled.", _conversationId, _participantRole, _streamRotationCounter);
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[{ConversationId}][{Role}] Fatal error on stream #{Rotation}", _conversationId, _participantRole, _streamRotationCounter);
                OnStateChanged(StreamSessionState.Faulted, "Fatal stream exception", ex);
                break;
            }
            finally
            {
                duplexCall?.Dispose();
            }

            if (!shouldRotate && !isErrorRestart)
            {
                _logger.LogInformation("[{ConversationId}][{Role}] Stream #{Rotation} completed naturally.", _conversationId, _participantRole, _streamRotationCounter);
                break;
            }

            OnStateChanged(StreamSessionState.Rotated, $"Rotated stream #{_streamRotationCounter}");
        }

        OnStateChanged(StreamSessionState.Completed, "Session streaming worker ended");
    }

    private static bool IsTransientRpcException(RpcException ex)
    {
        return ex.StatusCode is StatusCode.DeadlineExceeded
            or StatusCode.Unavailable
            or StatusCode.Aborted
            or StatusCode.Internal
            or StatusCode.ResourceExhausted;
    }

    private void OnTranscriptReceived(StreamingRecognitionResult result)
    {
        TranscriptReceived?.Invoke(this, new TranscriptEventArgs(
            _conversationId, _participantId, _participantRole, result));
    }

    private void OnSuggestionReceived(AnalyzeContentResponse response)
    {
        SuggestionReceived?.Invoke(this, new SuggestionEventArgs(
            _conversationId, _participantId, _participantRole, response));
    }

    private void OnStateChanged(StreamSessionState state, string message, Exception? exception = null)
    {
        StateChanged?.Invoke(this, new StreamStateEventArgs(
            _conversationId, _participantId, state, message, exception));
    }

    /// <summary>
    /// Signals the end of the voice stream and completes the session gracefully.
    /// </summary>
    public async Task StopAsync()
    {
        if (_disconnectRequested) return;
        _disconnectRequested = true;

        _logger.LogInformation("[{ConversationId}][{Role}] Stopping session...", _conversationId, _participantRole);
        _audioChannel.Writer.TryComplete();

        if (_sessionWorkerTask != null)
        {
            try
            {
                await _sessionWorkerTask;
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "[{ConversationId}] Session worker task error during shutdown", _conversationId);
            }
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_isDisposed) return;
        _isDisposed = true;

        await StopAsync();

        _cts.Cancel();
        _audioBuffer.Dispose();
        _cts.Dispose();
    }
}
