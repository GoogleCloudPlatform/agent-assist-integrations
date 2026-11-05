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
/// Event arguments for Agent Assist suggestions (Articles, Smart Replies, Dialogflow actions).
/// </summary>
public class SuggestionEventArgs : EventArgs
{
    public string ConversationId { get; }
    public string ParticipantId { get; }
    public string ParticipantRole { get; }
    public AnalyzeContentResponse Response { get; }

    public SuggestionEventArgs(
        string conversationId,
        string participantId,
        string participantRole,
        AnalyzeContentResponse response)
    {
        ConversationId = conversationId;
        ParticipantId = participantId;
        ParticipantRole = participantRole;
        Response = response;
    }
}
