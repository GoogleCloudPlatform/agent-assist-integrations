# Google Cloud Dialogflow Bidi-SAC .NET 8 Reference Architecture

[![.NET 8](https://img.shields.io/badge/.NET-8.0-blue.svg)](https://dotnet.microsoft.com/download/dotnet/8.0)
[![gRPC](https://img.shields.io/badge/gRPC-v2.67-green.svg)](https://grpc.io/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Agent%20Assist-orange.svg)](https://cloud.google.com/agent-assist)
[![Tests](https://img.shields.io/badge/Tests-53%20Passed-brightgreen.svg)]()

A high-performance, production-grade .NET 8 C# reference architecture and library for **Google Cloud Dialogflow v2beta1 Bidirectional Streaming Analyze Content (`BidiStreamingAnalyzeContent`)**, ported directly from battle-tested CCaaS voice integrations.

Designed as an authoritative reference pattern for **NICE CXone** (whose connector runs on modern .NET 8 on Linux using `grpc-dotnet`), **Five9**, **Genesys Cloud**, and other enterprise Contact Center as a Service (CCaaS) platforms integrating with Google Cloud Agent Assist.

---

## Architecture & Problem Overview

When integrating CCaaS voice streams with Dialogflow Agent Assist, enterprise connector implementations frequently encounter four critical production pitfalls:

```mermaid
sequenceDiagram
    autonumber
    participant CCaaS as CCaaS Voice Engine (NICE CXone / Five9)
    participant Session as DialogflowBidiStreamSession
    participant Buffer as CircularAudioBuffer (ArrayPool)
    participant DF as Google Cloud Dialogflow (Bidi-SAC)

    Note over CCaaS,DF: 1. Stream Initialization & Voice Config
    CCaaS->>Session: Start()
    Session->>DF: BidiStreamingAnalyzeContent() [Open Duplex Stream #1]
    Session->>DF: Config(Participant, AudioEncoding, SampleRate)

    Note over CCaaS,DF: 2. Continuous Multi-Turn Speech (Resolution of b/573603541)
    loop Active Conversation (Turns 1 to N across ~14.5 minutes)
        CCaaS->>Session: PushAudio(20ms RTP frame)
        Session->>Buffer: Write(frame)
        Session->>DF: Input.Audio(chunk)
        DF-->>Session: RecognitionResult(is_final: false, interim transcript)
        DF-->>Session: RecognitionResult(is_final: true, speech_end_offset: t1)
        DF-->>Session: AnalyzeContentResponse(Agent Assist suggestions)
        Note over Session,DF: STREAM REMAINS OPEN! DO NOT CLOSE ON is_final!
    end

    Note over CCaaS,DF: 3. Boundary-Safe Rotation (Elapsed > 14m 30s)
    DF-->>Session: RecognitionResult(is_final: true, speech_end_offset: t_boundary)
    Note over Session: Threshold crossed! Rotate at sentence boundary.
    Session->>Buffer: ExtractLookbackAudio(lastFinalOffset, 1.5s max)
    Session->>DF: RequestStream.CompleteAsync() [Stream #1 EOF]
    Session->>DF: BidiStreamingAnalyzeContent() [Open Duplex Stream #2]
    Session->>DF: Config(...)
    Session->>DF: Input.Audio(LookbackPayload) [Zero Audio Clipping]
    
    Note over CCaaS,DF: 4. Graceful Teardown
    CCaaS->>Session: StopAsync()
    Session->>DF: RequestStream.CompleteAsync()
    Session->>DF: Drain ResponseStream (2s timeout fallback)
    CCaaS->>DF: CompleteConversationAsync()
```

### 1. The "Turn-Taking" Fallacy ([b/573603541](https://b.corp.google.com/issues/573603541))
* **Anti-pattern:** Closing and recreating the gRPC duplex stream every time an `is_final: true` transcript event is received.
* **Production Impact:** Extreme socket thrashing, latency spikes, severed interim speech on subsequent sentences, broken Agent Assist contextual memory, and premature stream closure causing transcription to permanently freeze mid-call.
* **Authoritative Solution:** Maintain a **single long-lived duplex stream** across speaker turns, pauses, and sentences. Turns are logical events inside the recognition stream, not stream boundaries.

### 2. The 15-Minute Deadline & Boundary-Safe Rotation
* **Constraint:** Google Cloud Dialogflow enforces a strict ~15-minute deadline per streaming gRPC call (`DEADLINE_EXCEEDED`).
* **Anti-pattern:** Cutting the stream abruptly when a timer fires, truncating the customer or agent mid-word or mid-sentence.
* **Authoritative Solution:** `DialogflowBidiStreamSession` tracks elapsed stream time and rotates **only at sentence boundaries** (`is_final == true`) once the threshold (~14.5 minutes) is crossed. A fallback safety cutoff at 14m 50s protects against edge-case deadlocks (e.g. caller put on hold for 15+ minutes).

### 3. The Audio Lookback & Clipping Problem
* **Challenge:** During the milliseconds required to close stream $N$ and open stream $N+1$, the user may continue speaking. Audio sent during the cutover or immediately following the last final speech offset can be lost.
* **Authoritative Solution:** An internal circular ring buffer (`CircularAudioBuffer`) continuously records trailing raw audio frames in a zero-allocation `ArrayPool<byte>`. On stream rotation or transient retry, trailing audio recorded past the last `SpeechEndOffset` (up to 1.5 seconds) is extracted and prepended to the new stream request before piping live audio.

### 4. Clean Lifecycle Teardown & Deadlock Prevention
* **Anti-pattern:** Calling `CompleteConversation` while the gRPC audio stream is still actively open (triggers `FAILED_PRECONDITION`), or hanging indefinitely awaiting response EOF if remote endpoints stall.
* **Authoritative Solution:** Structured async disposal: draining the audio channel, calling `RequestStream.CompleteAsync()`, awaiting response completion with a graceful 2-second timeout fallback (`readTask.WaitAsync(2s)`), and then invoking `CompleteConversationAsync()`.

---

## Architectural Mapping: Python `asyncio` to .NET 8

| Python Implementation (`five9/mediastream-grpc`) | .NET 8 C# Equivalent | Design Detail |
| :--- | :--- | :--- |
| `bidi_streaming_analyze_content()` | `AsyncDuplexStreamingCall<BidiStreamingAnalyzeContentRequest, BidiStreamingAnalyzeContentResponse>` | Built into `Google.Cloud.Dialogflow.V2Beta1` via `ParticipantsClient`. |
| Request Generator (`async def gen_requests()`) | `System.Threading.Channels.Channel<ReadOnlyMemory<byte>>` | Thread-safe, non-blocking single-reader producer-consumer buffer between RTP audio and gRPC streaming writer. |
| Response Loop (`async for response in responses`) | `await foreach (var response in call.ResponseStream.ReadAllAsync(cancellationToken))` | Fully asynchronous, non-blocking response processing. |
| Audio Ring Buffer (`collections.deque`) | `CircularAudioBuffer` (`ArrayPool<byte>`) | Fixed-size zero-allocation circular buffer that slices trailing audio based on `SpeechEndOffset`. |
| Session Rotation (`time.time() - start > THRESHOLD`) | `Stopwatch` + Utterance Boundary Check | Evaluates at ~14.5 minutes on `result.IsFinal == true`. |

---

## Solution Structure

```
samples/dotnet-bidi-streaming/
├── DialogflowBidiStream.sln
├── Makefile                                 # Build, test, and CLI runner commands
├── Dockerfile                               # Multi-stage build with test verification
├── src/
│   └── DialogflowBidiStream/                # Core reusable .NET 8 library
│       ├── DialogflowBidiStream.csproj
│       ├── Buffers/
│       │   └── CircularAudioBuffer.cs        # High-performance audio ring buffer
│       ├── Core/
│       │   └── DialogflowBidiStreamSession.cs # 14.5m boundary rotation & bidi session
│       ├── Extensions/
│       │   └── ServiceCollectionExtensions.cs # .NET 8 Dependency Injection
│       ├── Five9/
│       │   └── Five9VoiceServiceImpl.cs      # VoiceStream gRPC servicer implementation
│       ├── Management/
│       │   └── DialogflowConversationManager.cs # Conversation & participant lifecycle
│       ├── Models/
│       │   ├── DialogflowStreamingOptions.cs # Configuration settings
│       │   ├── StreamStateEventArgs.cs       # Lifecycle events
│       │   ├── SuggestionEventArgs.cs        # Agent Assist suggestion events
│       │   └── TranscriptEventArgs.cs        # Real-time transcript events
│       └── Protos/
│           └── voice.proto                   # Five9 VoiceStream proto specification
├── samples/
│   ├── CliStreamer/                         # Runnable CLI Audio Streamer (ADC credentials)
│   │   ├── CliStreamer.csproj
│   │   ├── Program.cs                        # Real-time audio streaming console app
│   │   └── test_data/
│   │       └── sample_8k.mulaw               # Bundled 8kHz test audio
│   └── DialogflowBidiStream.Sample/          # Minimal ASP.NET Core gRPC server host
│       ├── DialogflowBidiStream.Sample.csproj
│       ├── Program.cs
│       └── appsettings.json
└── tests/
    └── DialogflowBidiStream.Tests/
        ├── DialogflowBidiStream.Tests.csproj
        ├── TestDoubles/
        │   └── TestStreamDoubles.cs          # In-memory gRPC stream harnesses & doubles
        ├── Unit/
        │   ├── TurnTakingAntiPatternTests.cs # Explicit verification of b/573603541 multi-turn stability
        │   ├── LookbackBufferMathTests.cs    # Byte-accurate lookback slicing math (8kHz & 16kHz)
        │   ├── TeardownLifecycleTests.cs     # Clean closure ordering & deadlock prevention
        │   ├── CircularAudioBufferTests.cs   # Ring buffer capacity & wrap-around
        │   ├── DialogflowBidiStreamSessionTests.cs # Session lifecycle & arg validation
        │   ├── DialogflowConversationManagerTests.cs # 404/409 idempotent conversation lifecycle
        │   ├── DialogflowStreamingOptionsTests.cs # Option defaults & config validation
        │   ├── Five9VoiceServiceImplTests.cs # VoiceStream gRPC servicer & call leg mapping
        │   ├── ProtobufSerializationTests.cs # Voice proto wire format serialization
        │   └── ServiceCollectionExtensionsTests.cs # DI container registration
        ├── Integration/
        │   ├── DialogflowStreamingEndToEndTests.cs # Full end-to-end voice streaming flow
        │   ├── StreamRotationIntegrationTests.cs # Boundary-safe 14.5m rotation & lookback replay
        │   └── TransientFaultRetryTests.cs   # Transient gRPC failure recovery & backoff
        └── Load/
            ├── AudioStreamingLoadTests.cs    # 25-50 concurrent calls, memory & GC Gen 2 stability
            └── ChannelBackpressureAndBurstLoadTests.cs # Burst contention & simultaneous rotations
```

---

## Comprehensive Test Suite

The test suite contains **53 automated tests** structured to prove correctness across every enterprise edge case:

### Test Tiers & Key Coverage

#### 1. Unit Tests (`Category=Unit`)
* **`TurnTakingAntiPatternTests.cs` (Directly targeting [b/573603541](https://b.corp.google.com/issues/573603541))**:
  * Feeds 4 consecutive conversational turns with `is_final: true`.
  * Asserts that `session.RotationCount == 1`.
  * Asserts that `RequestStream.CompleteAsync()` is **not** called.
  * Proves that speaker turns do not close or recreate the underlying stream.
* **`LookbackBufferMathTests.cs`**:
  * Verifies byte-accurate lookback slicing for 8kHz $\mu$-law ($1\text{ byte/sample}$) and 16kHz Linear PCM ($2\text{ bytes/sample}$).
  * Asserts that trailing audio between speech offset ($t = 2.0\text{s}$) and rotation ($t = 2.8\text{s}$) produces exactly 6,400 bytes with byte-for-byte pattern fidelity.
  * Asserts lookback window capping when delta exceeds `MaxLookbackSeconds` ($1.5\text{s}$).
* **`TeardownLifecycleTests.cs`**:
  * Tests structured shutdown when audio is actively being pushed.
  * Asserts that `PushAudio()` after teardown gracefully drops frames without throwing `ObjectDisposedException`.
  * Verifies idempotency of multiple `DisposeAsync()` and `StopAsync()` invocations.
* **`DialogflowConversationManagerTests.cs`**:
  * Tests 404 creation, 409 `AlreadyExists` race condition recovery, path generation for `"global"` vs regional locations, and conversation completion handling `FailedPrecondition`.
* **`Five9VoiceServiceImplTests.cs`**:
  * Validates `StreamingConfig` protocol enforcement, 10-digit zero padding on numeric call IDs (`five9-0000009876`), and call leg role mapping (`Customer` $\to$ `EndUser`, `Agent` $\to$ `HumanAgent`).

#### 2. Integration Tests (`Category=Integration`)
* **`DialogflowStreamingEndToEndTests.cs`**:
  * End-to-end integration: client connects $\to$ sends config $\to$ receives start streaming ACK $\to$ streams audio frames $\to$ receives interim & final transcripts $\to$ disconnects $\to$ auto-completes conversation.
* **`StreamRotationIntegrationTests.cs`**:
  * Proves rotation is deferred during active speech and triggers on the first `is_final == true` utterance boundary after crossing the 14.5m threshold.
  * Proves fallback cutoff triggers if a caller remains silent or monologues past `MaxStreamLifetime` (14m 50s).
* **`TransientFaultRetryTests.cs`**:
  * Simulates transient gRPC errors (`StatusCode.Unavailable`, `DeadlineExceeded`, `ResourceExhausted`) and proves the session automatically reconnects Stream #2 with lookback audio.
  * Proves fatal errors (`PermissionDenied`) transition to `Faulted` and exit cleanly.

#### 3. Load & Stress Tests (`Category=Load`)
* **`AudioStreamingLoadTests.cs`**:
  * Runs 25 concurrent calls streaming 20ms frames simultaneously without packet loss or deadlocks.
  * Streams 10,000+ packets through the ring buffer, asserting that Gen 2 GC collections remain $\le 5$ collections due to `ArrayPool` reuse.
* **`ChannelBackpressureAndBurstLoadTests.cs`**:
  * Pushes rapid bursts of 3,000 packets across 10 parallel producer tasks into a single session under lock-free contention.
  * Simulates 10 concurrent active sessions undergoing stream rotation at the exact same instant under ongoing audio streaming.

---

## Running the Tests

Tests can be executed locally with `dotnet test` or inside the containerized SDK via `make`:

```bash
# Run all 53 unit, integration, and load tests
make test

# Run unit tests only (44 tests)
make test-unit

# Run integration tests only (5 tests)
make test-integration

# Run load and stress tests only (4 tests)
make test-load
```

---

## Running the CLI Audio Streamer (`CliStreamer`)

A runnable console application is provided in `samples/CliStreamer` to allow partner engineers to stream audio to their own Google Cloud project using **Application Default Credentials (ADC)**.

### Prerequisites

```bash
gcloud auth application-default login
```

### Run against your GCP Project

```bash
# Using Makefile
PROJECT_ID="your-project-id" \
CONVERSATION_PROFILE_NAME="projects/your-project-id/locations/global/conversationProfiles/your-profile" \
make stream-cli

# Or directly with dotnet CLI
dotnet run --project samples/CliStreamer -- \
  --project "your-project-id" \
  --profile "projects/your-project-id/locations/global/conversationProfiles/your-profile" \
  --audio "path/to/audio_8k.mulaw"
```

### Live Output Example

```text
================================================================================
  Google Cloud Dialogflow Bidi-SAC .NET 8 Audio Streamer CLI
  Authoritative Reference Pattern for Agent Assist Real-Time Voice
================================================================================
[Audio] Using bundled test audio: test_data/sample_8k.mulaw
[Auth] Initializing Google Cloud Dialogflow gRPC Clients via ADC...
[Session] Conversation ID: cli-20261106000246-a1b2c3
[Session] Role:            HUMAN_AGENT
[Session] Audio Format:    Mulaw @ 8000Hz (32,000 bytes)

[State Changed] Connected: Stream #1 connected
[Streaming] Piping audio (160 bytes every 20ms)... Press Ctrl+C to stop.

[Interim] I need help with my reservation...
>>> [FINAL TRANSCRIPT] (Offset: 2450ms): "I need help with my reservation"
[Agent Assist Suggestion Received]: Suggestion: "Article: How to change reservations" (Confidence: 0.94)

[Streaming] Finished sending 32,000 bytes in 4.02s.
[Session] Closing stream and completing conversation...
[Success] Dialogflow Bidi-SAC streaming session completed successfully.
```

---

## Direct CCaaS Integration (NICE CXone Agent Assist Hub)

If you are embedding the session directly into an existing CCaaS connector service:

```csharp
// 1. Resolve conversation and participant
var conversation = await conversationManager.GetOrCreateConversationAsync(callId);
var participant = await conversationManager.CreateParticipantAsync(callId, Participant.Types.Role.HumanAgent);
string participantId = participant.Name.Split("/participants/").Last();

// 2. Instantiate and wire session
await using var session = new DialogflowBidiStreamSession(
    participantsClient,
    conversationId: callId,
    participantId: participantId,
    participantRole: "HUMAN_AGENT",
    options: optionsSnapshot,
    logger: logger);

session.TranscriptReceived += (sender, e) =>
{
    if (e.IsFinal)
    {
        Console.WriteLine($"[Final Transcript]: {e.Transcript}");
    }
};

session.SuggestionReceived += (sender, e) =>
{
    Console.WriteLine($"[Agent Assist Suggestion]: {e.Response}");
};

// 3. Start streaming worker
session.Start();

// 4. Pipe incoming raw audio frames (MULAW 8kHz or PCM 16kHz)
while (callIsActive)
{
    byte[] rtpFrame = await ReceiveNextRtpAudioChunkAsync();
    session.PushAudio(rtpFrame);
}

// 5. Clean teardown
await session.StopAsync();
await conversationManager.CompleteConversationAsync(callId);
```

---

## References

* [Google Cloud Agent Assist Bidi-Streaming API](https://docs.cloud.google.com/gemini-enterprise-cx/agent-assist/bidi-stream-api)
* [Google Cloud Agent Assist Voice Integration with Five9](https://docs.cloud.google.com/gemini-enterprise-cx/agent-assist/priv/five9-voice)
* [Google.Cloud.Dialogflow.V2Beta1 .NET Reference](https://docs.cloud.google.com/dotnet/docs/reference/Google.Cloud.Dialogflow.V2Beta1/latest)
* [Issue Tracker: b/573603541](https://b.corp.google.com/issues/573603541)
