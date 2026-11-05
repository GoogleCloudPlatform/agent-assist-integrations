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

namespace DialogflowBidiStream.Models;

public enum StreamSessionState
{
    Initialized,
    Starting,
    Connected,
    Rotating,
    Rotated,
    Retrying,
    Completed,
    Faulted
}

/// <summary>
/// Event arguments tracking stream lifecycle state changes.
/// </summary>
public class StreamStateEventArgs : EventArgs
{
    public string ConversationId { get; }
    public string ParticipantId { get; }
    public StreamSessionState State { get; }
    public string Message { get; }
    public Exception? Exception { get; }

    public StreamStateEventArgs(
        string conversationId,
        string participantId,
        StreamSessionState state,
        string message,
        Exception? exception = null)
    {
        ConversationId = conversationId;
        ParticipantId = participantId;
        State = state;
        Message = message;
        Exception = exception;
    }
}
