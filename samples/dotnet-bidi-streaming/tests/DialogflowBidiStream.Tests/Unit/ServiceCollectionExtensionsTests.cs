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

using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using DialogflowBidiStream.Extensions;
using DialogflowBidiStream.Five9;
using DialogflowBidiStream.Management;
using DialogflowBidiStream.Models;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class ServiceCollectionExtensionsTests
{
    [Fact]
    public void AddDialogflowStreaming_WithOptionsAction_RegistersServicesAndBindsOptions()
    {
        var services = new ServiceCollection();
        services.AddLogging();

        services.AddDialogflowStreaming(options =>
        {
            options.ProjectId = "my-test-proj";
            options.LocationId = "us-central1";
            options.ConversationProfileName = "projects/my-test-proj/locations/us-central1/conversationProfiles/cp-test";
            options.DefaultSampleRateHertz = 16000;
        });

        // Verify service descriptors
        Assert.Contains(services, d => d.ServiceType == typeof(IDialogflowConversationManager) && d.ImplementationType == typeof(DialogflowConversationManager));
        Assert.Contains(services, d => d.ServiceType == typeof(Five9VoiceServiceImpl));

        var sp = services.BuildServiceProvider();
        var optionsSnapshot = sp.GetRequiredService<IOptions<DialogflowStreamingOptions>>().Value;

        Assert.Equal("my-test-proj", optionsSnapshot.ProjectId);
        Assert.Equal("us-central1", optionsSnapshot.LocationId);
        Assert.Equal("projects/my-test-proj/locations/us-central1/conversationProfiles/cp-test", optionsSnapshot.ConversationProfileName);
        Assert.Equal(16000, optionsSnapshot.DefaultSampleRateHertz);
    }

    [Fact]
    public void AddDialogflowStreaming_WithConfiguration_BindsSectionCorrectly()
    {
        var inMemoryConfig = new Dictionary<string, string?>
        {
            ["DialogflowStreaming:ProjectId"] = "cfg-proj",
            ["DialogflowStreaming:LocationId"] = "europe-west1",
            ["DialogflowStreaming:ConversationProfileName"] = "projects/cfg-proj/locations/europe-west1/conversationProfiles/cp-eu",
            ["DialogflowStreaming:MaxLookbackSeconds"] = "2.0",
            ["DialogflowStreaming:DefaultSampleRateHertz"] = "8000"
        };

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(inMemoryConfig)
            .Build();

        var services = new ServiceCollection();
        services.AddLogging();
        services.AddDialogflowStreaming(configuration);

        var sp = services.BuildServiceProvider();
        var optionsSnapshot = sp.GetRequiredService<IOptions<DialogflowStreamingOptions>>().Value;

        Assert.Equal("cfg-proj", optionsSnapshot.ProjectId);
        Assert.Equal("europe-west1", optionsSnapshot.LocationId);
        Assert.Equal(2.0, optionsSnapshot.MaxLookbackSeconds);
        Assert.Equal(8000, optionsSnapshot.DefaultSampleRateHertz);
    }
}
