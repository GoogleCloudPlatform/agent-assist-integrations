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
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Models;

namespace DialogflowBidiStream.Management;

/// <summary>
/// Service interface for managing Dialogflow Conversations and Participants.
/// </summary>
public interface IDialogflowConversationManager
{
    Task<Conversation> GetOrCreateConversationAsync(
        string conversationId,
        string? conversationProfileName = null,
        CancellationToken cancellationToken = default);

    Task<Participant> CreateParticipantAsync(
        string conversationId,
        Participant.Types.Role role,
        CancellationToken cancellationToken = default);

    Task<Conversation?> CompleteConversationAsync(
        string conversationId,
        CancellationToken cancellationToken = default);

    Task<ConversationProfile?> GetConversationProfileAsync(
        string conversationProfileName,
        CancellationToken cancellationToken = default);

    Task<bool> ValidateConversationProfileAsync(
        string conversationProfileName,
        CancellationToken cancellationToken = default);
}

/// <summary>
/// Production implementation of Dialogflow conversation lifecycle management.
/// Handles idempotent creation, resource naming, and graceful cleanup.
/// </summary>
public class DialogflowConversationManager : IDialogflowConversationManager
{
    private readonly ConversationsClient _conversationsClient;
    private readonly ConversationProfilesClient _conversationProfilesClient;
    private readonly ParticipantsClient _participantsClient;
    private readonly DialogflowStreamingOptions _options;
    private readonly ILogger<DialogflowConversationManager> _logger;

    public DialogflowConversationManager(
        ConversationsClient conversationsClient,
        ConversationProfilesClient conversationProfilesClient,
        ParticipantsClient participantsClient,
        IOptions<DialogflowStreamingOptions> options,
        ILogger<DialogflowConversationManager> logger)
    {
        _conversationsClient = conversationsClient ?? throw new ArgumentNullException(nameof(conversationsClient));
        _conversationProfilesClient = conversationProfilesClient ?? throw new ArgumentNullException(nameof(conversationProfilesClient));
        _participantsClient = participantsClient ?? throw new ArgumentNullException(nameof(participantsClient));
        _options = options?.Value ?? throw new ArgumentNullException(nameof(options));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Gets an existing conversation or creates a new one idempotently.
    /// </summary>
    public async Task<Conversation> GetOrCreateConversationAsync(
        string conversationId,
        string? conversationProfileName = null,
        CancellationToken cancellationToken = default)
    {
        string projectId = _options.ProjectId;
        string locationId = _options.LocationId;
        string profile = !string.IsNullOrWhiteSpace(conversationProfileName)
            ? conversationProfileName
            : _options.ConversationProfileName;

        if (string.IsNullOrWhiteSpace(profile))
        {
            throw new InvalidOperationException("ConversationProfileName must be configured in options or provided as an argument.");
        }

        // Format parent name: projects/{project}/locations/{location}
        string parent = locationId.Equals("global", StringComparison.OrdinalIgnoreCase)
            ? $"projects/{projectId}"
            : $"projects/{projectId}/locations/{locationId}";

        string conversationName = locationId.Equals("global", StringComparison.OrdinalIgnoreCase)
            ? $"projects/{projectId}/conversations/{conversationId}"
            : $"projects/{projectId}/locations/{locationId}/conversations/{conversationId}";

        // Attempt retrieval first
        try
        {
            var existing = await _conversationsClient.GetConversationAsync(
                new GetConversationRequest { Name = conversationName },
                cancellationToken: cancellationToken);

            _logger.LogInformation("[{ConversationId}] Retrieved existing conversation: {Name} (State: {State})",
                conversationId, existing.Name, existing.LifecycleState);
            return existing;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.NotFound)
        {
            _logger.LogDebug("[{ConversationId}] Conversation not found, creating new...", conversationId);
        }

        // Create new conversation
        var newConversation = new Conversation
        {
            ConversationProfile = profile
        };

        var createRequest = new CreateConversationRequest
        {
            Parent = parent,
            Conversation = newConversation,
            ConversationId = conversationId
        };

        try
        {
            var created = await _conversationsClient.CreateConversationAsync(
                createRequest,
                cancellationToken: cancellationToken);

            _logger.LogInformation("[{ConversationId}] Created new conversation: {Name} (State: {State})",
                conversationId, created.Name, created.LifecycleState);
            return created;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.AlreadyExists)
        {
            _logger.LogInformation("[{ConversationId}] Conversation already exists, fetching existing...", conversationId);
            return await _conversationsClient.GetConversationAsync(
                new GetConversationRequest { Name = conversationName },
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[{ConversationId}] Failed to create conversation", conversationId);
            throw;
        }
    }

    /// <summary>
    /// Creates a participant (Human Agent or End User) inside an existing conversation.
    /// </summary>
    public async Task<Participant> CreateParticipantAsync(
        string conversationId,
        Participant.Types.Role role,
        CancellationToken cancellationToken = default)
    {
        string projectId = _options.ProjectId;
        string locationId = _options.LocationId;

        string parent = locationId.Equals("global", StringComparison.OrdinalIgnoreCase)
            ? $"projects/{projectId}/conversations/{conversationId}"
            : $"projects/{projectId}/locations/{locationId}/conversations/{conversationId}";

        var participant = new Participant
        {
            Role = role
        };

        try
        {
            var created = await _participantsClient.CreateParticipantAsync(
                new CreateParticipantRequest
                {
                    Parent = parent,
                    Participant = participant
                },
                cancellationToken: cancellationToken);

            _logger.LogInformation("[{ConversationId}][{Role}] Created participant: {ParticipantName}",
                conversationId, role, created.Name);
            return created;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[{ConversationId}][{Role}] Failed to create participant", conversationId, role);
            throw;
        }
    }

    /// <summary>
    /// Gracefully completes the specified conversation. Finished conversations are purged after 30 days.
    /// </summary>
    public async Task<Conversation?> CompleteConversationAsync(
        string conversationId,
        CancellationToken cancellationToken = default)
    {
        string projectId = _options.ProjectId;
        string locationId = _options.LocationId;

        string conversationName = locationId.Equals("global", StringComparison.OrdinalIgnoreCase)
            ? $"projects/{projectId}/conversations/{conversationId}"
            : $"projects/{projectId}/locations/{locationId}/conversations/{conversationId}";

        try
        {
            var completed = await _conversationsClient.CompleteConversationAsync(
                new CompleteConversationRequest { Name = conversationName },
                cancellationToken: cancellationToken);

            _logger.LogInformation("[{ConversationId}] Conversation completed successfully: {Name}",
                conversationId, completed.Name);
            return completed;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.NotFound)
        {
            _logger.LogWarning("[{ConversationId}] Conversation not found when attempting completion.", conversationId);
            return null;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.FailedPrecondition)
        {
            _logger.LogWarning("[{ConversationId}] Conversation already completed or invalid state: {Message}",
                conversationId, ex.Status.Detail);
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[{ConversationId}] Error completing conversation", conversationId);
            return null;
        }
    }

    /// <summary>
    /// Fetches the configured Conversation Profile to inspect STT / Agent Assist configuration.
    /// </summary>
    public async Task<ConversationProfile?> GetConversationProfileAsync(
        string conversationProfileName,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var profile = await _conversationProfilesClient.GetConversationProfileAsync(
                new GetConversationProfileRequest { Name = conversationProfileName },
                cancellationToken: cancellationToken);
            return profile;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to retrieve conversation profile {ProfileName}", conversationProfileName);
            return null;
        }
    }

    /// <summary>
    /// Validates whether the specified Conversation Profile has bidirectional streaming enabled (<c>use_bidi_streaming = true</c>).
    /// Logs a warning if bidirectional streaming is disabled, as downstream Agent Assist suggestion generators
    /// and quota allocation require this setting for optimal operation.
    /// </summary>
    public async Task<bool> ValidateConversationProfileAsync(
        string conversationProfileName,
        CancellationToken cancellationToken = default)
    {
        var profile = await GetConversationProfileAsync(conversationProfileName, cancellationToken);
        if (profile == null)
        {
            _logger.LogWarning("Unable to inspect ConversationProfile '{ProfileName}' for bidirectional streaming validation.", conversationProfileName);
            return false;
        }

        if (!profile.UseBidiStreaming)
        {
            _logger.LogWarning(
                "ConversationProfile '{ProfileName}' does not have 'use_bidi_streaming' enabled. " +
                "BidiStreamingAnalyzeContent requires 'use_bidi_streaming: true' on the ConversationProfile for optimal " +
                "downstream Agent Assist suggestions (Knowledge Assist, Smart Reply) and proper quota allocation.",
                conversationProfileName);
            return false;
        }

        _logger.LogInformation("ConversationProfile '{ProfileName}' validated: use_bidi_streaming is enabled.", conversationProfileName);
        return true;
    }
}
