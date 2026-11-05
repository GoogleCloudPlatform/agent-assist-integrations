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

namespace DialogflowBidiStream.Models;

/// <summary>
/// Configuration options for Dialogflow bidirectional streaming sessions.
/// </summary>
public class DialogflowStreamingOptions
{
    public const string SectionName = "DialogflowStreaming";

    /// <summary>
    /// Google Cloud Project ID hosting Dialogflow / Agent Assist.
    /// </summary>
    public string ProjectId { get; set; } = string.Empty;

    /// <summary>
    /// Google Cloud Region / Location ID (e.g., "global", "us-central1").
    /// </summary>
    public string LocationId { get; set; } = "global";

    /// <summary>
    /// Full resource name or ID of the Conversation Profile (e.g. "projects/{project}/locations/{location}/conversationProfiles/{id}").
    /// </summary>
    public string ConversationProfileName { get; set; } = string.Empty;

    /// <summary>
    /// Telephony sampling rate (default 8000 Hz).
    /// </summary>
    public int DefaultSampleRateHertz { get; set; } = 8000;

    /// <summary>
    /// Audio encoding (default MULAW for G.711 telephony, or LINEAR16).
    /// </summary>
    public AudioEncoding DefaultAudioEncoding { get; set; } = AudioEncoding.Mulaw;

    /// <summary>
    /// Maximum lookback window duration in seconds to preserve in circular buffer for rotation replay.
    /// Default is 1.5 seconds.
    /// </summary>
    public double MaxLookbackSeconds { get; set; } = 1.5;

    /// <summary>
    /// Threshold after which the session safely rotates to a new gRPC stream upon the next final transcript.
    /// Dialogflow limits streaming calls to ~15 minutes (900 seconds). Default is 14.5 minutes (870 seconds).
    /// </summary>
    public TimeSpan RestartThreshold { get; set; } = TimeSpan.FromMinutes(14.5);

    /// <summary>
    /// Maximum lifetime before a forced rotation if no sentence boundary is detected.
    /// Default is 14 minutes 50 seconds.
    /// </summary>
    public TimeSpan MaxStreamLifetime { get; set; } = TimeSpan.FromMinutes(14.83);

    /// <summary>
    /// Default language code for Speech-to-Text transcription.
    /// </summary>
    public string LanguageCode { get; set; } = "en-US";

    /// <summary>
    /// Automatically complete the conversation in Dialogflow when client disconnects.
    /// </summary>
    public bool AutoCompleteConversationOnDisconnect { get; set; } = true;

    /// <summary>
    /// Enable detailed verbose logging of intermediate transcripts and audio frames.
    /// </summary>
    public bool EnableDebugLogging { get; set; } = false;
}
