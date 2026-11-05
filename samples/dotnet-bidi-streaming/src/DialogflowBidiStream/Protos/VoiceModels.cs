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

using Google.Protobuf;
using Google.Protobuf.Reflection;
using Google.Protobuf.WellKnownTypes;

namespace Five9.VoiceStream.Grpc;

public sealed class VoiceConfig : IMessage<VoiceConfig>
{
    public static MessageParser<VoiceConfig> Parser { get; } = new(() => new VoiceConfig());

    public static class Types
    {
        public enum AudioEncoding
        {
            EncodingUnspecified = 0,
            Linear16 = 1,
            Mulaw = 2,
            Amr = 3,
            AmrWb = 4
        }
    }

    public Types.AudioEncoding Encoding { get; set; } = Types.AudioEncoding.EncodingUnspecified;
    public int SampleRateHertz { get; set; } = 8000;

    public MessageDescriptor Descriptor => null!;

    public VoiceConfig Clone() => new()
    {
        Encoding = Encoding,
        SampleRateHertz = SampleRateHertz
    };

    public bool Equals(VoiceConfig? other) =>
        other is not null && Encoding == other.Encoding && SampleRateHertz == other.SampleRateHertz;

    public override bool Equals(object? obj) => Equals(obj as VoiceConfig);
    public override int GetHashCode() => HashCode.Combine(Encoding, SampleRateHertz);

    public void MergeFrom(VoiceConfig other)
    {
        if (other is null) return;
        Encoding = other.Encoding;
        SampleRateHertz = other.SampleRateHertz;
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            switch (tag)
            {
                case 8: // 1 << 3 | 0
                    Encoding = (Types.AudioEncoding)input.ReadEnum();
                    break;
                case 16: // 2 << 3 | 0
                    SampleRateHertz = input.ReadInt32();
                    break;
                default:
                    input.SkipLastField();
                    break;
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (Encoding != Types.AudioEncoding.EncodingUnspecified)
        {
            output.WriteTag(1, WireFormat.WireType.Varint);
            output.WriteEnum((int)Encoding);
        }
        if (SampleRateHertz != 0)
        {
            output.WriteTag(2, WireFormat.WireType.Varint);
            output.WriteInt32(SampleRateHertz);
        }
    }

    public int CalculateSize()
    {
        int size = 0;
        if (Encoding != Types.AudioEncoding.EncodingUnspecified)
        {
            size += 1 + CodedOutputStream.ComputeEnumSize((int)Encoding);
        }
        if (SampleRateHertz != 0)
        {
            size += 1 + CodedOutputStream.ComputeInt32Size(SampleRateHertz);
        }
        return size;
    }
}

public sealed class StreamingConfig : IMessage<StreamingConfig>
{
    public static MessageParser<StreamingConfig> Parser { get; } = new(() => new StreamingConfig());

    public static class Types
    {
        public enum CallLeg
        {
            Agent = 0,
            Customer = 1,
            Supervisor = 2
        }
    }

    public VoiceConfig? VoiceConfig { get; set; }
    public string VccCallId { get; set; } = string.Empty;
    public string DomainId { get; set; } = string.Empty;
    public string CampaignId { get; set; } = string.Empty;
    public string AgentId { get; set; } = string.Empty;
    public Types.CallLeg CallLeg { get; set; } = Types.CallLeg.Agent;
    public string TrustToken { get; set; } = string.Empty;
    public string SubscriptionId { get; set; } = string.Empty;
    public string SkillId { get; set; } = string.Empty;

    public MessageDescriptor Descriptor => null!;

    public StreamingConfig Clone() => new()
    {
        VoiceConfig = VoiceConfig?.Clone(),
        VccCallId = VccCallId,
        DomainId = DomainId,
        CampaignId = CampaignId,
        AgentId = AgentId,
        CallLeg = CallLeg,
        TrustToken = TrustToken,
        SubscriptionId = SubscriptionId,
        SkillId = SkillId
    };

    public bool Equals(StreamingConfig? other) =>
        other is not null &&
        Equals(VoiceConfig, other.VoiceConfig) &&
        VccCallId == other.VccCallId &&
        CallLeg == other.CallLeg;

    public override bool Equals(object? obj) => Equals(obj as StreamingConfig);
    public override int GetHashCode() => HashCode.Combine(VccCallId, CallLeg);

    public void MergeFrom(StreamingConfig other)
    {
        if (other is null) return;
        if (other.VoiceConfig != null)
        {
            VoiceConfig ??= new VoiceConfig();
            VoiceConfig.MergeFrom(other.VoiceConfig);
        }
        VccCallId = other.VccCallId;
        DomainId = other.DomainId;
        CampaignId = other.CampaignId;
        AgentId = other.AgentId;
        CallLeg = other.CallLeg;
        TrustToken = other.TrustToken;
        SubscriptionId = other.SubscriptionId;
        SkillId = other.SkillId;
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            switch (tag)
            {
                case 10: // 1: message
                    VoiceConfig ??= new VoiceConfig();
                    input.ReadMessage(VoiceConfig);
                    break;
                case 18: // 2: string
                    VccCallId = input.ReadString();
                    break;
                case 26: // 3: string
                    DomainId = input.ReadString();
                    break;
                case 34: // 4: string
                    CampaignId = input.ReadString();
                    break;
                case 42: // 5: string
                    AgentId = input.ReadString();
                    break;
                case 48: // 6: enum
                    CallLeg = (Types.CallLeg)input.ReadEnum();
                    break;
                case 58: // 7: string
                    TrustToken = input.ReadString();
                    break;
                case 66: // 8: string
                    SubscriptionId = input.ReadString();
                    break;
                case 74: // 9: string
                    SkillId = input.ReadString();
                    break;
                default:
                    input.SkipLastField();
                    break;
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (VoiceConfig != null)
        {
            output.WriteTag(1, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(VoiceConfig);
        }
        if (!string.IsNullOrEmpty(VccCallId))
        {
            output.WriteTag(2, WireFormat.WireType.LengthDelimited);
            output.WriteString(VccCallId);
        }
        if (!string.IsNullOrEmpty(DomainId))
        {
            output.WriteTag(3, WireFormat.WireType.LengthDelimited);
            output.WriteString(DomainId);
        }
        if (!string.IsNullOrEmpty(CampaignId))
        {
            output.WriteTag(4, WireFormat.WireType.LengthDelimited);
            output.WriteString(CampaignId);
        }
        if (!string.IsNullOrEmpty(AgentId))
        {
            output.WriteTag(5, WireFormat.WireType.LengthDelimited);
            output.WriteString(AgentId);
        }
        if (CallLeg != Types.CallLeg.Agent)
        {
            output.WriteTag(6, WireFormat.WireType.Varint);
            output.WriteEnum((int)CallLeg);
        }
        if (!string.IsNullOrEmpty(TrustToken))
        {
            output.WriteTag(7, WireFormat.WireType.LengthDelimited);
            output.WriteString(TrustToken);
        }
        if (!string.IsNullOrEmpty(SubscriptionId))
        {
            output.WriteTag(8, WireFormat.WireType.LengthDelimited);
            output.WriteString(SubscriptionId);
        }
        if (!string.IsNullOrEmpty(SkillId))
        {
            output.WriteTag(9, WireFormat.WireType.LengthDelimited);
            output.WriteString(SkillId);
        }
    }

    public int CalculateSize()
    {
        int size = 0;
        if (VoiceConfig != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(VoiceConfig);
        }
        if (!string.IsNullOrEmpty(VccCallId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(VccCallId);
        }
        if (!string.IsNullOrEmpty(DomainId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(DomainId);
        }
        if (!string.IsNullOrEmpty(CampaignId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(CampaignId);
        }
        if (!string.IsNullOrEmpty(AgentId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(AgentId);
        }
        if (CallLeg != Types.CallLeg.Agent)
        {
            size += 1 + CodedOutputStream.ComputeEnumSize((int)CallLeg);
        }
        if (!string.IsNullOrEmpty(TrustToken))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(TrustToken);
        }
        if (!string.IsNullOrEmpty(SubscriptionId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(SubscriptionId);
        }
        if (!string.IsNullOrEmpty(SkillId))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(SkillId);
        }
        return size;
    }
}

public sealed class StreamingStatus : IMessage<StreamingStatus>
{
    public static MessageParser<StreamingStatus> Parser { get; } = new(() => new StreamingStatus());

    public static class Types
    {
        public enum StatusCode
        {
            Success = 0,
            CltCallEnded = 1,
            CltCallHold = 2,
            CltCallResume = 3,
            CltDisconnect = 4,
            CltErrorNoResource = 100,
            CltErrorTimeout = 101,
            CltErrorGeneric = 102,
            SrvReqStartStreaming = 1001,
            SrvReqPauseStreaming = 1002,
            SrvReqDisconnect = 1011,
            SrvReqReconnect = 1012,
            SrvErrorNoResource = 1100,
            SrvErrorTimeout = 1101,
            SrvErrorGeneric = 1102
        }
    }

    public Types.StatusCode Code { get; set; } = Types.StatusCode.Success;
    public string Message { get; set; } = string.Empty;

    public MessageDescriptor Descriptor => null!;

    public StreamingStatus Clone() => new() { Code = Code, Message = Message };
    public bool Equals(StreamingStatus? other) => other is not null && Code == other.Code && Message == other.Message;
    public override bool Equals(object? obj) => Equals(obj as StreamingStatus);
    public override int GetHashCode() => HashCode.Combine(Code, Message);

    public void MergeFrom(StreamingStatus other)
    {
        if (other is null) return;
        Code = other.Code;
        Message = other.Message;
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            switch (tag)
            {
                case 8:
                    Code = (Types.StatusCode)input.ReadEnum();
                    break;
                case 18:
                    Message = input.ReadString();
                    break;
                default:
                    input.SkipLastField();
                    break;
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (Code != Types.StatusCode.Success)
        {
            output.WriteTag(1, WireFormat.WireType.Varint);
            output.WriteEnum((int)Code);
        }
        if (!string.IsNullOrEmpty(Message))
        {
            output.WriteTag(2, WireFormat.WireType.LengthDelimited);
            output.WriteString(Message);
        }
    }

    public int CalculateSize()
    {
        int size = 0;
        if (Code != Types.StatusCode.Success)
        {
            size += 1 + CodedOutputStream.ComputeEnumSize((int)Code);
        }
        if (!string.IsNullOrEmpty(Message))
        {
            size += 1 + CodedOutputStream.ComputeStringSize(Message);
        }
        return size;
    }
}

public sealed class StreamingFeedback : IMessage<StreamingFeedback>
{
    public static MessageParser<StreamingFeedback> Parser { get; } = new(() => new StreamingFeedback());

    public VoiceConfig? VoiceConfig { get; set; }

    public MessageDescriptor Descriptor => null!;
    public StreamingFeedback Clone() => new() { VoiceConfig = VoiceConfig?.Clone() };
    public bool Equals(StreamingFeedback? other) => other is not null && Equals(VoiceConfig, other.VoiceConfig);
    public override bool Equals(object? obj) => Equals(obj as StreamingFeedback);
    public override int GetHashCode() => VoiceConfig?.GetHashCode() ?? 0;

    public void MergeFrom(StreamingFeedback other)
    {
        if (other?.VoiceConfig != null)
        {
            VoiceConfig ??= new VoiceConfig();
            VoiceConfig.MergeFrom(other.VoiceConfig);
        }
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            if (tag == 10)
            {
                VoiceConfig ??= new VoiceConfig();
                input.ReadMessage(VoiceConfig);
            }
            else
            {
                input.SkipLastField();
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (VoiceConfig != null)
        {
            output.WriteTag(1, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(VoiceConfig);
        }
    }

    public int CalculateSize() =>
        VoiceConfig != null ? 1 + CodedOutputStream.ComputeMessageSize(VoiceConfig) : 0;
}

public sealed class StreamingVoiceRequest : IMessage<StreamingVoiceRequest>
{
    public static MessageParser<StreamingVoiceRequest> Parser { get; } = new(() => new StreamingVoiceRequest());

    public enum StreamingRequestOneofCase
    {
        None = 0,
        StreamingConfig = 1,
        AudioContent = 2,
        StreamingStatus = 3
    }

    private StreamingConfig? _streamingConfig;
    private ByteString _audioContent = ByteString.Empty;
    private StreamingStatus? _streamingStatus;

    public StreamingRequestOneofCase StreamingRequestCase { get; private set; } = StreamingRequestOneofCase.None;

    public StreamingConfig? StreamingConfig
    {
        get => _streamingConfig;
        set
        {
            _streamingConfig = value;
            StreamingRequestCase = value is null ? StreamingRequestOneofCase.None : StreamingRequestOneofCase.StreamingConfig;
        }
    }

    public ByteString AudioContent
    {
        get => _audioContent;
        set
        {
            _audioContent = value ?? ByteString.Empty;
            StreamingRequestCase = value is null ? StreamingRequestOneofCase.None : StreamingRequestOneofCase.AudioContent;
        }
    }

    public StreamingStatus? StreamingStatus
    {
        get => _streamingStatus;
        set
        {
            _streamingStatus = value;
            StreamingRequestCase = value is null ? StreamingRequestOneofCase.None : StreamingRequestOneofCase.StreamingStatus;
        }
    }

    public Timestamp? SendTime { get; set; }

    public MessageDescriptor Descriptor => null!;

    public StreamingVoiceRequest Clone()
    {
        var copy = new StreamingVoiceRequest { SendTime = SendTime?.Clone() };
        switch (StreamingRequestCase)
        {
            case StreamingRequestOneofCase.StreamingConfig:
                copy.StreamingConfig = StreamingConfig?.Clone();
                break;
            case StreamingRequestOneofCase.AudioContent:
                copy.AudioContent = AudioContent;
                break;
            case StreamingRequestOneofCase.StreamingStatus:
                copy.StreamingStatus = StreamingStatus?.Clone();
                break;
        }
        return copy;
    }

    public bool Equals(StreamingVoiceRequest? other) => other is not null && StreamingRequestCase == other.StreamingRequestCase;
    public override bool Equals(object? obj) => Equals(obj as StreamingVoiceRequest);
    public override int GetHashCode() => (int)StreamingRequestCase;

    public void MergeFrom(StreamingVoiceRequest other)
    {
        if (other is null) return;
        if (other.SendTime != null)
        {
            SendTime ??= new Timestamp();
            SendTime.MergeFrom(other.SendTime);
        }
        switch (other.StreamingRequestCase)
        {
            case StreamingRequestOneofCase.StreamingConfig:
                if (other.StreamingConfig != null)
                {
                    StreamingConfig ??= new StreamingConfig();
                    StreamingConfig.MergeFrom(other.StreamingConfig);
                }
                break;
            case StreamingRequestOneofCase.AudioContent:
                AudioContent = other.AudioContent;
                break;
            case StreamingRequestOneofCase.StreamingStatus:
                if (other.StreamingStatus != null)
                {
                    StreamingStatus ??= new StreamingStatus();
                    StreamingStatus.MergeFrom(other.StreamingStatus);
                }
                break;
        }
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            switch (tag)
            {
                case 10: // 1: StreamingConfig
                    StreamingConfig = new StreamingConfig();
                    input.ReadMessage(StreamingConfig);
                    break;
                case 18: // 2: bytes
                    AudioContent = input.ReadBytes();
                    break;
                case 26: // 3: StreamingStatus
                    StreamingStatus = new StreamingStatus();
                    input.ReadMessage(StreamingStatus);
                    break;
                case 34: // 4: Timestamp
                    SendTime ??= new Timestamp();
                    input.ReadMessage(SendTime);
                    break;
                default:
                    input.SkipLastField();
                    break;
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (StreamingConfig != null)
        {
            output.WriteTag(1, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(StreamingConfig);
        }
        else if (AudioContent.Length > 0)
        {
            output.WriteTag(2, WireFormat.WireType.LengthDelimited);
            output.WriteBytes(AudioContent);
        }
        else if (StreamingStatus != null)
        {
            output.WriteTag(3, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(StreamingStatus);
        }
        if (SendTime != null)
        {
            output.WriteTag(4, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(SendTime);
        }
    }

    public int CalculateSize()
    {
        int size = 0;
        if (StreamingConfig != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(StreamingConfig);
        }
        else if (AudioContent.Length > 0)
        {
            size += 1 + CodedOutputStream.ComputeBytesSize(AudioContent);
        }
        else if (StreamingStatus != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(StreamingStatus);
        }
        if (SendTime != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(SendTime);
        }
        return size;
    }
}

public sealed class StreamingVoiceResponse : IMessage<StreamingVoiceResponse>
{
    public static MessageParser<StreamingVoiceResponse> Parser { get; } = new(() => new StreamingVoiceResponse());

    public StreamingStatus? Status { get; set; }
    public StreamingFeedback? Feedback { get; set; }

    public MessageDescriptor Descriptor => null!;

    public StreamingVoiceResponse Clone() => new()
    {
        Status = Status?.Clone(),
        Feedback = Feedback?.Clone()
    };

    public bool Equals(StreamingVoiceResponse? other) =>
        other is not null && Equals(Status, other.Status) && Equals(Feedback, other.Feedback);

    public override bool Equals(object? obj) => Equals(obj as StreamingVoiceResponse);
    public override int GetHashCode() => HashCode.Combine(Status, Feedback);

    public void MergeFrom(StreamingVoiceResponse other)
    {
        if (other is null) return;
        if (other.Status != null)
        {
            Status ??= new StreamingStatus();
            Status.MergeFrom(other.Status);
        }
        if (other.Feedback != null)
        {
            Feedback ??= new StreamingFeedback();
            Feedback.MergeFrom(other.Feedback);
        }
    }

    public void MergeFrom(CodedInputStream input)
    {
        uint tag;
        while ((tag = input.ReadTag()) != 0)
        {
            switch (tag)
            {
                case 10:
                    Status ??= new StreamingStatus();
                    input.ReadMessage(Status);
                    break;
                case 18:
                    Feedback ??= new StreamingFeedback();
                    input.ReadMessage(Feedback);
                    break;
                default:
                    input.SkipLastField();
                    break;
            }
        }
    }

    public void WriteTo(CodedOutputStream output)
    {
        if (Status != null)
        {
            output.WriteTag(1, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(Status);
        }
        if (Feedback != null)
        {
            output.WriteTag(2, WireFormat.WireType.LengthDelimited);
            output.WriteMessage(Feedback);
        }
    }

    public int CalculateSize()
    {
        int size = 0;
        if (Status != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(Status);
        }
        if (Feedback != null)
        {
            size += 1 + CodedOutputStream.ComputeMessageSize(Feedback);
        }
        return size;
    }
}
