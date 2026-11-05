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

using Five9.VoiceStream.Grpc;
using Google.Protobuf;
using Xunit;

namespace DialogflowBidiStream.Tests.Unit;

[Trait("Category", "Unit")]
public class ProtobufSerializationTests
{
    [Fact]
    public void StreamingConfig_RoundTripsThroughProtobufWireFormat()
    {
        var config = new StreamingConfig
        {
            VccCallId = "1234567890",
            CallLeg = StreamingConfig.Types.CallLeg.Customer,
            DomainId = "domain-test",
            CampaignId = "campaign-100",
            AgentId = "agent-xyz",
            VoiceConfig = new VoiceConfig
            {
                Encoding = VoiceConfig.Types.AudioEncoding.Mulaw,
                SampleRateHertz = 8000
            }
        };

        byte[] bytes = config.ToByteArray();
        Assert.NotEmpty(bytes);

        var deserialized = StreamingConfig.Parser.ParseFrom(bytes);
        Assert.NotNull(deserialized);
        Assert.Equal("1234567890", deserialized.VccCallId);
        Assert.Equal(StreamingConfig.Types.CallLeg.Customer, deserialized.CallLeg);
        Assert.Equal("domain-test", deserialized.DomainId);
        Assert.NotNull(deserialized.VoiceConfig);
        Assert.Equal(VoiceConfig.Types.AudioEncoding.Mulaw, deserialized.VoiceConfig.Encoding);
        Assert.Equal(8000, deserialized.VoiceConfig.SampleRateHertz);
    }

    [Fact]
    public void StreamingVoiceRequest_AudioContent_RoundTripsAccurately()
    {
        byte[] rawAudio = new byte[] { 0x10, 0x20, 0x30, 0x40, 0x50 };
        var request = new StreamingVoiceRequest
        {
            AudioContent = ByteString.CopyFrom(rawAudio)
        };

        Assert.Equal(StreamingVoiceRequest.StreamingRequestOneofCase.AudioContent, request.StreamingRequestCase);

        byte[] bytes = request.ToByteArray();
        var parsed = StreamingVoiceRequest.Parser.ParseFrom(bytes);

        Assert.Equal(StreamingVoiceRequest.StreamingRequestOneofCase.AudioContent, parsed.StreamingRequestCase);
        Assert.Equal(rawAudio, parsed.AudioContent.ToByteArray());
    }

    [Fact]
    public void StreamingVoiceResponse_StartStreamingStatus_RoundTripsAccurately()
    {
        var response = new StreamingVoiceResponse
        {
            Status = new StreamingStatus
            {
                Code = StreamingStatus.Types.StatusCode.SrvReqStartStreaming,
                Message = "Start sending audio!"
            }
        };

        byte[] bytes = response.ToByteArray();
        var parsed = StreamingVoiceResponse.Parser.ParseFrom(bytes);

        Assert.NotNull(parsed.Status);
        Assert.Equal(StreamingStatus.Types.StatusCode.SrvReqStartStreaming, parsed.Status.Code);
        Assert.Equal("Start sending audio!", parsed.Status.Message);
    }
}
