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
/// Event arguments for real-time speech recognition results.
/// </summary>
public class TranscriptEventArgs : EventArgs
{
    public string ConversationId { get; }
    public string ParticipantId { get; }
    public string ParticipantRole { get; }
    public StreamingRecognitionResult RecognitionResult { get; }
    public string Transcript => RecognitionResult.Transcript;
    public bool IsFinal => RecognitionResult.IsFinal;
    public float Stability => RecognitionResult.Stability;
    public float Confidence => RecognitionResult.Confidence;
    public TimeSpan SpeechEndOffset => RecognitionResult.SpeechEndOffset?.ToTimeSpan() ?? TimeSpan.Zero;

    public TranscriptEventArgs(
        string conversationId,
        string participantId,
        string participantRole,
        StreamingRecognitionResult recognitionResult)
    {
        ConversationId = conversationId;
        ParticipantId = participantId;
        ParticipantRole = participantRole;
        RecognitionResult = recognitionResult;
    }
}
