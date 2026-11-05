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
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using DialogflowBidiStream.Five9;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;

namespace DialogflowBidiStream.Extensions;

/// <summary>
/// Extension methods for configuring Dialogflow bidirectional streaming in .NET 8 dependency injection.
/// </summary>
public static class ServiceCollectionExtensions
{
    /// <summary>
    /// Adds Dialogflow Bidi-SAC streaming services, conversation management, and client singletons.
    /// </summary>
    public static IServiceCollection AddDialogflowStreaming(
        this IServiceCollection services,
        Action<DialogflowStreamingOptions> configureOptions)
    {
        services.Configure(configureOptions);
        RegisterDialogflowServices(services);
        return services;
    }

    /// <summary>
    /// Adds Dialogflow Bidi-SAC streaming services bound to a configuration section.
    /// </summary>
    public static IServiceCollection AddDialogflowStreaming(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.Configure<DialogflowStreamingOptions>(configuration.GetSection(DialogflowStreamingOptions.SectionName));
        RegisterDialogflowServices(services);
        return services;
    }

    private static void RegisterDialogflowServices(IServiceCollection services)
    {
        // Google Cloud Dialogflow gRPC Client Singletons
        // Reusing client instances across sessions prevents socket exhaustion and optimizes connection pooling
        services.TryAddSingleton(sp => new ConversationsClientBuilder().Build());
        services.TryAddSingleton(sp => new ConversationProfilesClientBuilder().Build());
        services.TryAddSingleton(sp => new ParticipantsClientBuilder().Build());

        // Conversation Lifecycle Management
        services.TryAddSingleton<IDialogflowConversationManager, DialogflowConversationManager>();

        // Five9 Voice gRPC Service
        services.TryAddScoped<Five9VoiceServiceImpl>();
    }
}
