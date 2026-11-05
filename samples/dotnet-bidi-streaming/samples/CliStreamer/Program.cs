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
using Google.Cloud.Dialogflow.V2Beta1;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Core;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;

namespace DialogflowBidiStream.CliStreamer;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        Console.ForegroundColor = ConsoleColor.White;
        Console.WriteLine("================================================================================");
        Console.WriteLine("  Google Cloud Dialogflow Bidi-SAC .NET 8 Audio Streamer CLI");
        Console.WriteLine("  Authoritative Reference Pattern for Agent Assist Real-Time Voice");
        Console.WriteLine("================================================================================");
        Console.ResetColor();

        // Parse CLI arguments
        var parsedArgs = ParseArguments(args);

        if (parsedArgs.ContainsKey("help") || parsedArgs.ContainsKey("h"))
        {
            PrintUsage();
            return 0;
        }

        string projectId = parsedArgs.GetValueOrDefault("project") ?? System.Environment.GetEnvironmentVariable("PROJECT_ID") ?? "";
        string locationId = parsedArgs.GetValueOrDefault("location") ?? System.Environment.GetEnvironmentVariable("LOCATION_ID") ?? "global";
        if (string.IsNullOrWhiteSpace(locationId)) locationId = "global";
        string profileName = parsedArgs.GetValueOrDefault("profile") ?? System.Environment.GetEnvironmentVariable("CONVERSATION_PROFILE_NAME") ?? "";
        string audioPath = parsedArgs.GetValueOrDefault("audio") ?? "";
        string roleStr = parsedArgs.GetValueOrDefault("role") ?? "HUMAN_AGENT";
        int sampleRate = int.TryParse(parsedArgs.GetValueOrDefault("rate"), out int r) ? r : 8000;
        string encodingStr = parsedArgs.GetValueOrDefault("encoding") ?? "Mulaw";

        if (string.IsNullOrWhiteSpace(projectId) || string.IsNullOrWhiteSpace(profileName))
        {
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("\n[Notice] Missing required GCP configuration.");
            Console.ResetColor();
            Console.WriteLine("Please provide --project and --profile (or set PROJECT_ID and CONVERSATION_PROFILE_NAME).\n");
            PrintUsage();
            return 1;
        }

        var encoding = encodingStr.Equals("Linear16", StringComparison.OrdinalIgnoreCase)
            ? AudioEncoding.Linear16
            : AudioEncoding.Mulaw;

        var participantRole = roleStr.Equals("END_USER", StringComparison.OrdinalIgnoreCase)
            ? Participant.Types.Role.EndUser
            : Participant.Types.Role.HumanAgent;

        // Locate or generate audio
        byte[] audioBytes;
        if (!string.IsNullOrWhiteSpace(audioPath) && File.Exists(audioPath))
        {
            Console.WriteLine($"[Audio] Reading audio file: {audioPath}");
            audioBytes = await File.ReadAllBytesAsync(audioPath);
        }
        else
        {
            string defaultTestData = Path.Combine(AppContext.BaseDirectory, "test_data", "sample_8k.mulaw");
            if (File.Exists(defaultTestData))
            {
                Console.WriteLine($"[Audio] Using bundled test audio: {defaultTestData}");
                audioBytes = await File.ReadAllBytesAsync(defaultTestData);
            }
            else
            {
                Console.WriteLine("[Audio] Generating synthetic 5-second 8kHz audio signal...");
                audioBytes = GenerateSyntheticMulawAudio(seconds: 5.0, sampleRate: sampleRate);
            }
        }

        // Setup Logger
        using var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.AddSimpleConsole(options =>
            {
                options.IncludeScopes = false;
                options.SingleLine = true;
                options.TimestampFormat = "HH:mm:ss.fff ";
            });
            builder.SetMinimumLevel(LogLevel.Information);
        });
        var logger = loggerFactory.CreateLogger("CliStreamer");

        // Options
        var streamingOptions = Options.Create(new DialogflowStreamingOptions
        {
            ProjectId = projectId,
            LocationId = locationId,
            ConversationProfileName = profileName,
            DefaultSampleRateHertz = sampleRate,
            DefaultAudioEncoding = encoding,
            MaxLookbackSeconds = 1.5,
            RestartThreshold = TimeSpan.FromMinutes(14.5),
            MaxStreamLifetime = TimeSpan.FromMinutes(14.83)
        });

        // Instantiate Google Cloud Clients using Application Default Credentials (ADC)
        Console.WriteLine("\n[Auth] Initializing Google Cloud Dialogflow gRPC Clients via ADC...");
        var conversationsClient = await new ConversationsClientBuilder().BuildAsync();
        var conversationProfilesClient = await new ConversationProfilesClientBuilder().BuildAsync();
        var participantsClient = await new ParticipantsClientBuilder().BuildAsync();

        var conversationManager = new DialogflowConversationManager(
            conversationsClient,
            conversationProfilesClient,
            participantsClient,
            streamingOptions,
            loggerFactory.CreateLogger<DialogflowConversationManager>());

        string callId = $"cli-{DateTime.UtcNow:yyyyMMddHHmmss}-{Guid.NewGuid():N}"[..26];

        Console.ForegroundColor = ConsoleColor.Cyan;
        Console.WriteLine($"[Session] Conversation ID: {callId}");
        Console.WriteLine($"[Session] Role:            {roleStr}");
        Console.WriteLine($"[Session] Audio Format:    {encoding} @ {sampleRate}Hz ({audioBytes.Length:N0} bytes)");
        Console.ResetColor();

        // 1. Create conversation & participant
        Console.WriteLine("[Session] Resolving Dialogflow conversation and participant...");
        var conversation = await conversationManager.GetOrCreateConversationAsync(callId);
        var participant = await conversationManager.CreateParticipantAsync(callId, participantRole);
        string participantId = participant.Name.Split("/participants/").Last();

        // 2. Initialize Bidi-SAC Session
        await using var session = new DialogflowBidiStreamSession(
            participantsClient,
            callId,
            participantId,
            roleStr,
            streamingOptions,
            loggerFactory.CreateLogger<DialogflowBidiStreamSession>());

        // 3. Subscribe to real-time events
        session.TranscriptReceived += (sender, e) =>
        {
            if (e.IsFinal)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine($"\n>>> [FINAL TRANSCRIPT] (Offset: {e.SpeechEndOffset.TotalMilliseconds:F0}ms): \"{e.Transcript}\"");
                Console.ResetColor();
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.DarkGray;
                Console.Write($"\r[Interim] {e.Transcript}                                          ");
                Console.ResetColor();
            }
        };

        session.SuggestionReceived += (sender, e) =>
        {
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine($"\n[Agent Assist Suggestion Received]: {e.Response}");
            Console.ResetColor();
        };

        session.StateChanged += (sender, e) =>
        {
            Console.ForegroundColor = ConsoleColor.Magenta;
            Console.WriteLine($"[State Changed] {e.State}: {e.Message}");
            Console.ResetColor();
        };

        // 4. Start streaming worker
        session.Start();

        // Hook Ctrl+C
        using var cts = new CancellationTokenSource();
        Console.CancelKeyPress += (s, ev) =>
        {
            ev.Cancel = true;
            cts.Cancel();
            Console.WriteLine("\n[Ctrl+C] Stopping stream gracefully...");
        };

        // 5. Pipe audio in 20ms frames in real-time
        int bytesPerSample = encoding == AudioEncoding.Mulaw ? 1 : 2;
        int frameSize = (int)(0.020 * sampleRate * bytesPerSample); // 20ms = 160 bytes for 8kHz 1B
        int offset = 0;
        var sw = Stopwatch.StartNew();

        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine($"\n[Streaming] Piping audio ({frameSize} bytes every 20ms)... Press Ctrl+C to stop.\n");
        Console.ResetColor();

        while (offset < audioBytes.Length && !cts.IsCancellationRequested)
        {
            int length = Math.Min(frameSize, audioBytes.Length - offset);
            byte[] chunk = new byte[length];
            Buffer.BlockCopy(audioBytes, offset, chunk, 0, length);

            session.PushAudio(chunk);
            offset += length;

            // Wait 20ms to simulate real-time RTP telephony pacing
            await Task.Delay(20, cts.Token).ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);
        }

        sw.Stop();
        Console.WriteLine($"\n\n[Streaming] Finished sending {offset:N0} bytes in {sw.Elapsed.TotalSeconds:F2}s. Waiting 3s for final ASR/suggestions to drain...");
        await Task.Delay(3000, cts.Token).ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);

        // 6. Graceful shutdown
        Console.WriteLine("[Session] Closing stream and completing conversation...");
        await session.StopAsync();
        await conversationManager.CompleteConversationAsync(callId);

        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine("[Success] Dialogflow Bidi-SAC streaming session completed successfully.\n");
        Console.ResetColor();
        return 0;
    }

    private static Dictionary<string, string> ParseArguments(string[] args)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < args.Length; i++)
        {
            string arg = args[i];
            if (arg.StartsWith("--"))
            {
                string key = arg[2..];
                if (i + 1 < args.Length && !args[i + 1].StartsWith("--"))
                {
                    result[key] = args[++i];
                }
                else
                {
                    result[key] = "true";
                }
            }
            else if (arg.StartsWith('-'))
            {
                result[arg[1..]] = "true";
            }
        }
        return result;
    }

    private static void PrintUsage()
    {
        Console.WriteLine("Usage: dotnet run --project samples/CliStreamer -- [options]\n");
        Console.WriteLine("Options:");
        Console.WriteLine("  --project <ID>       GCP Project ID (or env PROJECT_ID)");
        Console.WriteLine("  --location <LOC>     GCP Location/Region ID (default: global)");
        Console.WriteLine("  --profile <NAME>     Conversation Profile Name (or env CONVERSATION_PROFILE_NAME)");
        Console.WriteLine("  --audio <PATH>       Path to raw audio file (default: bundled sample)");
        Console.WriteLine("  --role <ROLE>        HUMAN_AGENT (default) or END_USER");
        Console.WriteLine("  --rate <HERTZ>       Sample rate: 8000 (default) or 16000");
        Console.WriteLine("  --encoding <ENC>     Mulaw (default) or Linear16");
        Console.WriteLine("  --help, -h           Show this help information\n");
        Console.WriteLine("Authentication:");
        Console.WriteLine("  Uses Google Application Default Credentials (ADC):");
        Console.WriteLine("  Run `gcloud auth application-default login` before streaming.\n");
    }

    private static byte[] GenerateSyntheticMulawAudio(double seconds, int sampleRate)
    {
        int totalSamples = (int)(seconds * sampleRate);
        byte[] output = new byte[totalSamples];

        // Generate 440Hz sine wave tone encoded into 8-bit mu-law
        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            short pcmSample = (short)(Math.Sin(2 * Math.PI * 440 * t) * 16000);
            output[i] = LinearToMuLaw(pcmSample);
        }
        return output;
    }

    private static byte LinearToMuLaw(short pcm)
    {
        const int BIAS = 0x84;
        const int CLIP = 32635;

        int sign = (pcm >> 8) & 0x80;
        if (sign != 0) pcm = (short)-pcm;
        if (pcm > CLIP) pcm = CLIP;
        pcm = (short)(pcm + BIAS);

        int exponent = 7;
        for (int expMask = 0x4000; (pcm & expMask) == 0 && exponent > 0; exponent--, expMask >>= 1) { }

        int mantissa = (pcm >> (exponent + 3)) & 0x0F;
        byte mulaw = (byte)~(sign | (exponent << 4) | mantissa);
        return mulaw;
    }
}
