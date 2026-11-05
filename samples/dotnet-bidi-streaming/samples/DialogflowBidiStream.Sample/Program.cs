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

using DialogflowBidiStream.Extensions;
using DialogflowBidiStream.Five9;

var builder = WebApplication.CreateBuilder(args);

// 1. Add gRPC services and gRPC reflection for debugging with grpcurl
builder.Services.AddGrpc(options =>
{
    options.EnableDetailedErrors = true;
    options.MaxReceiveMessageSize = 4 * 1024 * 1024; // 4MB
    options.MaxSendMessageSize = 4 * 1024 * 1024;
});
builder.Services.AddGrpcReflection();

// 2. Add Dialogflow Bidi-SAC Streaming and Conversation Management
builder.Services.AddDialogflowStreaming(builder.Configuration);

var app = builder.Build();

// 3. Map gRPC endpoints
app.MapGrpcService<Five9VoiceServiceImpl>();
app.MapGrpcReflectionService();

app.MapGet("/", () => Results.Ok(new
{
    Service = "Dialogflow Bidi-SAC Streaming Bridge (.NET 8)",
    Status = "Healthy",
    Timestamp = DateTimeOffset.UtcNow
}));

app.Run();
