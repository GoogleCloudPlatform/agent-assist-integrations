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
using DialogflowBidiStream.Models;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class DialogflowStreamingOptionsTests
{
    [Fact]
    public void DefaultOptions_HaveExpectedProductionValues()
    {
        var options = new DialogflowStreamingOptions();

        Assert.Equal("DialogflowStreaming", DialogflowStreamingOptions.SectionName);
        Assert.Equal(string.Empty, options.ProjectId);
        Assert.Equal("global", options.LocationId);
        Assert.Equal(string.Empty, options.ConversationProfileName);
        Assert.Equal(8000, options.DefaultSampleRateHertz);
        Assert.Equal(AudioEncoding.Mulaw, options.DefaultAudioEncoding);
        Assert.Equal(1.5, options.MaxLookbackSeconds);
        Assert.Equal(TimeSpan.FromMinutes(14.5), options.RestartThreshold);
        Assert.Equal(TimeSpan.FromMinutes(14.83), options.MaxStreamLifetime);
        Assert.Equal("en-US", options.LanguageCode);
        Assert.True(options.AutoCompleteConversationOnDisconnect);
        Assert.False(options.EnableDebugLogging);
    }

    [Fact]
    public void CustomOptions_CanBeConfigured()
    {
        var options = new DialogflowStreamingOptions
        {
            ProjectId = "custom-project",
            LocationId = "us-central1",
            ConversationProfileName = "projects/custom-project/locations/us-central1/conversationProfiles/cp-1",
            DefaultSampleRateHertz = 16000,
            DefaultAudioEncoding = AudioEncoding.Linear16,
            MaxLookbackSeconds = 2.5,
            RestartThreshold = TimeSpan.FromMinutes(10),
            MaxStreamLifetime = TimeSpan.FromMinutes(12),
            LanguageCode = "es-ES",
            AutoCompleteConversationOnDisconnect = false,
            EnableDebugLogging = true
        };

        Assert.Equal("custom-project", options.ProjectId);
        Assert.Equal("us-central1", options.LocationId);
        Assert.Equal("projects/custom-project/locations/us-central1/conversationProfiles/cp-1", options.ConversationProfileName);
        Assert.Equal(16000, options.DefaultSampleRateHertz);
        Assert.Equal(AudioEncoding.Linear16, options.DefaultAudioEncoding);
        Assert.Equal(2.5, options.MaxLookbackSeconds);
        Assert.Equal(TimeSpan.FromMinutes(10), options.RestartThreshold);
        Assert.Equal(TimeSpan.FromMinutes(12), options.MaxStreamLifetime);
        Assert.Equal("es-ES", options.LanguageCode);
        Assert.False(options.AutoCompleteConversationOnDisconnect);
        Assert.True(options.EnableDebugLogging);
    }
}
