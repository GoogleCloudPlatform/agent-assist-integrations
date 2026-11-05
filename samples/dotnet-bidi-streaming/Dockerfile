# Build Stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ["DialogflowBidiStream.sln", "./"]
COPY ["src/DialogflowBidiStream/DialogflowBidiStream.csproj", "src/DialogflowBidiStream/"]
COPY ["samples/DialogflowBidiStream.Sample/DialogflowBidiStream.Sample.csproj", "samples/DialogflowBidiStream.Sample/"]
COPY ["tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj", "tests/DialogflowBidiStream.Tests/"]

RUN dotnet restore

COPY . .

# Run Unit Tests during build
RUN dotnet test tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj -c Release

# Publish
WORKDIR /src/samples/DialogflowBidiStream.Sample
RUN dotnet publish -c Release -o /app/publish /p:UseAppHost=false

# Runtime Stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080

COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "DialogflowBidiStream.Sample.dll"]
