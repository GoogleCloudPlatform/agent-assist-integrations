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

using System.Threading.Channels;
using Google.Cloud.Dialogflow.V2Beta1;
using Grpc.Core;
using Moq;

namespace DialogflowBidiStream.Tests.TestDoubles;

/// <summary>
/// In-memory asynchronous stream reader for testing gRPC streams.
/// </summary>
public class TestAsyncStreamReader<T> : IAsyncStreamReader<T>
{
    private readonly Channel<T> _channel;
    private T _current = default!;

    public TestAsyncStreamReader()
    {
        _channel = Channel.CreateUnbounded<T>(new UnboundedChannelOptions
        {
            SingleReader = true,
            SingleWriter = false
        });
    }

    public T Current => _current;

    public void Enqueue(T item)
    {
        _channel.Writer.TryWrite(item);
    }

    public void Complete()
    {
        _channel.Writer.TryComplete();
    }

    public void Fail(Exception ex)
    {
        _channel.Writer.TryComplete(ex);
    }

    public async Task<bool> MoveNext(CancellationToken cancellationToken)
    {
        try
        {
            if (await _channel.Reader.WaitToReadAsync(cancellationToken))
            {
                if (_channel.Reader.TryRead(out var item))
                {
                    _current = item;
                    return true;
                }
            }
        }
        catch (OperationCanceledException)
        {
            return false;
        }
        return false;
    }
}

/// <summary>
/// In-memory client stream writer for recording requests and synchronizing in tests.
/// </summary>
public class TestClientStreamWriter<T> : IClientStreamWriter<T>
{
    private readonly List<T> _writtenMessages = new();
    private readonly object _lock = new();
    private readonly Channel<T> _channel = Channel.CreateUnbounded<T>();
    private readonly TaskCompletionSource _firstWriteTcs = new(TaskCreationOptions.RunContinuationsAsynchronously);

    public IReadOnlyList<T> WrittenMessages
    {
        get
        {
            lock (_lock)
            {
                return _writtenMessages.ToList();
            }
        }
    }

    public ChannelReader<T> Reader => _channel.Reader;
    public bool IsCompleted { get; private set; }
    public WriteOptions? WriteOptions { get; set; }
    public Action? OnCompleted { get; set; }

    public Task WriteAsync(T message)
    {
        lock (_lock)
        {
            _writtenMessages.Add(message);
        }
        _firstWriteTcs.TrySetResult();
        _channel.Writer.TryWrite(message);
        return Task.CompletedTask;
    }

    public Task CompleteAsync()
    {
        IsCompleted = true;
        _channel.Writer.TryComplete();
        OnCompleted?.Invoke();
        return Task.CompletedTask;
    }

    public async Task<bool> WaitForMessageCountAsync(int count, TimeSpan timeout)
    {
        using var cts = new CancellationTokenSource(timeout);
        while (!cts.IsCancellationRequested)
        {
            lock (_lock)
            {
                if (_writtenMessages.Count >= count)
                {
                    return true;
                }
            }
            try
            {
                await Task.Delay(10, cts.Token);
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
        return false;
    }
}

/// <summary>
/// In-memory server stream writer for recording responses sent by gRPC services.
/// </summary>
public class TestServerStreamWriter<T> : IServerStreamWriter<T>
{
    private readonly List<T> _written = new();
    private readonly object _lock = new();
    private readonly TaskCompletionSource _firstWriteTcs = new(TaskCreationOptions.RunContinuationsAsynchronously);

    public IReadOnlyList<T> WrittenMessages
    {
        get
        {
            lock (_lock)
            {
                return _written.ToList();
            }
        }
    }

    public WriteOptions? WriteOptions { get; set; }

    public Task WriteAsync(T message)
    {
        lock (_lock)
        {
            _written.Add(message);
        }
        _firstWriteTcs.TrySetResult();
        return Task.CompletedTask;
    }

    public async Task<bool> WaitForMessageCountAsync(int count, TimeSpan timeout)
    {
        using var cts = new CancellationTokenSource(timeout);
        while (!cts.IsCancellationRequested)
        {
            lock (_lock)
            {
                if (_written.Count >= count)
                {
                    return true;
                }
            }
            try
            {
                await Task.Delay(10, cts.Token);
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
        return false;
    }
}

/// <summary>
/// Helper to construct AsyncDuplexStreamingCall instances for testing.
/// </summary>
public static class TestGrpcCallHelper
{
    public static AsyncDuplexStreamingCall<TRequest, TResponse> CreateDuplexCall<TRequest, TResponse>(
        IClientStreamWriter<TRequest> requestStream,
        IAsyncStreamReader<TResponse> responseStream,
        Action? onDispose = null)
    {
        if (requestStream is TestClientStreamWriter<TRequest> testWriter &&
            responseStream is TestAsyncStreamReader<TResponse> testReader)
        {
            testWriter.OnCompleted = () => testReader.Complete();
        }

        return new AsyncDuplexStreamingCall<TRequest, TResponse>(
            requestStream,
            responseStream,
            Task.FromResult(new Metadata()),
            () => Status.DefaultSuccess,
            () => new Metadata(),
            () =>
            {
                if (responseStream is TestAsyncStreamReader<TResponse> tr)
                {
                    tr.Complete();
                }
                onDispose?.Invoke();
            });
    }
}

/// <summary>
/// Mock ServerCallContext for testing gRPC service implementations without a live network socket.
/// </summary>
public class TestServerCallContext : ServerCallContext
{
    private readonly Metadata _requestHeaders;
    private readonly CancellationToken _cancellationToken;
    private readonly Metadata _responseTrailers = new();
    private readonly AuthContext _authContext = new("test", new Dictionary<string, List<AuthProperty>>());
    private WriteOptions? _writeOptions;

    public TestServerCallContext(Metadata? requestHeaders = null, CancellationToken cancellationToken = default)
    {
        _requestHeaders = requestHeaders ?? new Metadata();
        _cancellationToken = cancellationToken;
    }

    protected override string MethodCore => "TestService/TestMethod";
    protected override string HostCore => "localhost";
    protected override string PeerCore => "ipv4:127.0.0.1:12345";
    protected override DateTime DeadlineCore => DateTime.UtcNow.AddMinutes(15);
    protected override Metadata RequestHeadersCore => _requestHeaders;
    protected override CancellationToken CancellationTokenCore => _cancellationToken;
    protected override Metadata ResponseTrailersCore => _responseTrailers;
    protected override Status StatusCore { get; set; } = Status.DefaultSuccess;
    protected override WriteOptions? WriteOptionsCore { get => _writeOptions; set => _writeOptions = value; }
    protected override AuthContext AuthContextCore => _authContext;

    protected override ContextPropagationToken CreatePropagationTokenCore(ContextPropagationOptions? options) =>
        throw new NotImplementedException();

    protected override Task WriteResponseHeadersAsyncCore(Metadata responseHeaders) =>
        Task.CompletedTask;
}

/// <summary>
/// Test fixture harness that sets up mock Dialogflow gRPC clients with stream tracking.
/// </summary>
public class DialogflowStreamingHarness
{
    public Mock<ParticipantsClient> MockParticipantsClient { get; } = new();
    public Mock<Participants.ParticipantsClient> MockGrpcClient { get; } = new();

    private readonly Queue<(TestClientStreamWriter<BidiStreamingAnalyzeContentRequest> RequestWriter, TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse> ResponseReader, AsyncDuplexStreamingCall<BidiStreamingAnalyzeContentRequest, BidiStreamingAnalyzeContentResponse> DuplexCall)> _streamQueue = new();

    public List<(TestClientStreamWriter<BidiStreamingAnalyzeContentRequest> RequestWriter, TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse> ResponseReader)> CreatedStreams { get; } = new();

    public DialogflowStreamingHarness()
    {
        MockParticipantsClient.SetupGet(c => c.GrpcClient).Returns(MockGrpcClient.Object);

        MockGrpcClient.Setup(g => g.BidiStreamingAnalyzeContent(
            It.IsAny<Metadata>(),
            It.IsAny<DateTime?>(),
            It.IsAny<CancellationToken>()))
            .Returns(() =>
            {
                if (_streamQueue.Count > 0)
                {
                    return _streamQueue.Dequeue().DuplexCall;
                }
                var defaultStream = CreateStream();
                return defaultStream.DuplexCall;
            });
    }

    public (TestClientStreamWriter<BidiStreamingAnalyzeContentRequest> RequestWriter, TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse> ResponseReader, AsyncDuplexStreamingCall<BidiStreamingAnalyzeContentRequest, BidiStreamingAnalyzeContentResponse> DuplexCall) EnqueueStream()
    {
        var stream = CreateStream();
        _streamQueue.Enqueue(stream);
        return stream;
    }

    private (TestClientStreamWriter<BidiStreamingAnalyzeContentRequest> RequestWriter, TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse> ResponseReader, AsyncDuplexStreamingCall<BidiStreamingAnalyzeContentRequest, BidiStreamingAnalyzeContentResponse> DuplexCall) CreateStream()
    {
        var requestWriter = new TestClientStreamWriter<BidiStreamingAnalyzeContentRequest>();
        var responseReader = new TestAsyncStreamReader<BidiStreamingAnalyzeContentResponse>();
        var duplexCall = TestGrpcCallHelper.CreateDuplexCall(requestWriter, responseReader);

        CreatedStreams.Add((requestWriter, responseReader));
        return (requestWriter, responseReader, duplexCall);
    }
}
