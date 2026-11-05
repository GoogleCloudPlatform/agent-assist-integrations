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
using Grpc.Core;

namespace Five9.VoiceStream.Grpc;

public static class Voice
{
    public const string ServiceName = "five9.voicestream.Voice";

    private static readonly Marshaller<StreamingVoiceRequest> __Marshaller_StreamingVoiceRequest =
        Marshallers.Create(
            (arg) => MessageExtensions.ToByteArray(arg),
            (bytes) => StreamingVoiceRequest.Parser.ParseFrom(bytes));

    private static readonly Marshaller<StreamingVoiceResponse> __Marshaller_StreamingVoiceResponse =
        Marshallers.Create(
            (arg) => MessageExtensions.ToByteArray(arg),
            (bytes) => StreamingVoiceResponse.Parser.ParseFrom(bytes));

    private static readonly Method<StreamingVoiceRequest, StreamingVoiceResponse> __Method_StreamingVoice =
        new Method<StreamingVoiceRequest, StreamingVoiceResponse>(
            MethodType.DuplexStreaming,
            ServiceName,
            "StreamingVoice",
            __Marshaller_StreamingVoiceRequest,
            __Marshaller_StreamingVoiceResponse);

    public abstract class VoiceBase
    {
        public virtual Task StreamingVoice(
            IAsyncStreamReader<StreamingVoiceRequest> requestStream,
            IServerStreamWriter<StreamingVoiceResponse> responseStream,
            ServerCallContext context)
        {
            throw new RpcException(new Status(StatusCode.Unimplemented, ""));
        }
    }

    public static ServerServiceDefinition BindService(VoiceBase serviceImpl)
    {
        return ServerServiceDefinition.CreateBuilder()
            .AddMethod(__Method_StreamingVoice, serviceImpl.StreamingVoice)
            .Build();
    }
}
