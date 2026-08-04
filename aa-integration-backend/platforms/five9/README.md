# Five9 MediaStream Integration Service

This service bridges Five9 Mediastream with Google Cloud Agent Assist, enabling real-time transcription and agent suggestions. It consists of two services:
1.  **gRPC Service**: Handles the bi-directional gRPC audio stream from Five9 MediaStream.
2.  **HTTP Service**: Presents Agent Assist UI modules and handles CTI and MediaStream events.

## System Architecture

The solution uses a split-service architecture to handle the distinct requirements of Five9's protocol: synchronous bi-directional audio streaming (gRPC) and asynchronous event handling (HTTP).

### High-Level Data Flow

1.  **Call Initiation**: Five9 triggers a CTI event to the **HTTP Service**, initiating the session.
2.  **Audio Streaming**: Five9 opens a secure WebSocket (upgraded to gRPC) connection to the **gRPC Service** for real-time audio exchange.
3.  **Processing**: The gRPC service forwards audio to Google Cloud Agent Assist CAIP.
4.  **Suggestions**: Agent Assist returns transcription and agent coaching suggestions, which are pushed to the **Frontend UI**.

## Component Design

### 1. gRPC Service (`mediastream-grpc`)
*   **Role**: Handles high-performance, real-time bi-directional audio streaming.
*   **Implementation**: Python gRPC server using `grpcio`.
*   **Concurrency**: Uses `grpc.aio` (AsyncIO) for high-performance non-blocking I/O.
*   **Protocol**: Defines the service contract via `mediastream-grpc/proto/voice.proto`.
*   **Core Module**: `VoiceServicer` implementation in `services/get_suggestions.py` orchestrates the audio stream handling and Agent Assist API calls.

### 2. HTTP Service (`mediastream-http`)
*   **Role**: Handles control plane events, token validation, and serving static UI assets.
*   **Implementation**: Flask web server.
*   **Endpoints**:
    *   `GET /`: Health check.
    *   `GET /agent-assist-ui-modules`: Serves the embedded agent widget.
    *   `GET /cti-call-event-destination/`: Validates the `FIVE9_TRUST_TOKEN` (returns SHA256 hash).
    *   `POST /cti-call-event-destination/`: Receives call metadata.
    *   `POST /mediastream-event-destination/subscriptions/<id>`: Receives async errors or status updates from the media stream.

## Security

*   **Trust Token**: The integration implements a shared-secret security model. A `FIVE9_TRUST_TOKEN` is generated and configured in both Five9 and the Cloud Run service. The HTTP service provides a validation endpoint (`GET /cti-call-event-destination/`) that returns the SHA256 hash of the configured token for verification.

## Deployment Guide

### Prerequisites

- **Google Cloud Project**: With Dialogflow and Agent Assist enabled.
- **Five9 Administrator Access**: To configure Mediastream subscription and Classic Connector.
- **Google Cloud CLI (`gcloud`)**: For Cloud Run deployment. [Install Guide](https://cloud.google.com/sdk/docs/install)
- **Make**: For running deployment scripts.
- **Docker or Podman**: For container building and local testing. The Makefile will automatically detect which one is installed and use it (preferring Docker).
    - [Docker Install Guide](https://docs.docker.com/get-docker/)
    - [Podman Install Guide](https://docs.podman.io/en/latest/installation.html)
- **grpcurl**: For verifying gRPC stream health. [Install Guide](https://github.com/fullstorydev/grpcurl#installation)

### 1. Configuration

1.  **Environment Variables**:
    Copy `.env.sample` to `.env` and configure the following:
    ```bash
    cp .env.sample .env
    ```

    | Variable | Description |
    | :--- | :--- |
    | `GRPC_SERVICE_NAME` | Name of the gRPC service container (used locally). |
    | `GRPC_PORT` | Port for the gRPC service (default: 50051). |
    | `HTTP_SERVICE_NAME` | Name of the HTTP service container (used locally). |
    | `HTTP_PORT` | Port for the HTTP service (default: 8080). |
    | `PROJECT_ID` | Your Google Cloud Project ID. |
    | `REGION` | The region where your Cloud Run services will be deployed. |
    | `FEATURES` | The features to enable for Agent Assist. See https://docs.cloud.google.com/agent-assist/docs/ui-modules for more information. |
    | `CONVERSATION_PROFILE_NAME` | The Agent Assist Conversation Profile Resource ID. |
    | `FIVE9_TRUST_TOKEN` | A secure token for validating Five9 requests (generated below). |
    | `FIVE9_API_KEY` | API Key for Five9. |

2.  **Generate Trust Token**:
    Run this command to generate a secure random token. Add the output to your `.env` file as `FIVE9_TRUST_TOKEN`.
    ```bash
    make generate-trust-token
    ```

### 2. Deploy to Google Cloud Run

Deploy both the gRPC and HTTP services to Cloud Run using the provided automation:

```bash
make deploy
```

This script will:
1.  Build the container images.
2.  Push them to Google Container Registry (GCR) or Artifact Registry.
3.  Deploy two Cloud Run services: one for gRPC (Voice) and one for HTTP (Events).
4.  Output the service URLs upon completion.

### 3. Five9 Configuration

Once deployed, configure Five9 to send streams to your service. Refer to the [Five9 MediaStream Technical Guide](https://documentation.five9.com/bundle/voicestream-dev-guide/resource/voicestream-dev-guide.pdf) for detailed steps.

1.  **Create an Event Stream Subscription**:
    *   **Destination URL**: Use the URL of your deployed **HTTP Service**.
    *   **Token**: Use the `FIVE9_TRUST_TOKEN` value you generated.

2.  **Configure Voice Stream**:
    *   **Destination**: Use the URL of your deployed **gRPC Service** (remove `https://` prefix if entering as a host/port, or follow Five9 specifics for gRPC targets).
    *   Enable **Bi-directional** streaming.

## Verification

To verify the deployment is reachable and functioning:

```bash
# Verify HTTP Service
make test-http-reachable

# Verify gRPC Service
make test-grpc-reachable
```

## Local Testing (Optional)

For troubleshooting or testing without deployment, you can run the services locally using Docker/Podman:

```bash
# Start services (down, build, up, logs)
make all
```

### Run Tests

To run all tests (reachability and unit tests):
```bash
make test
```

To run only unit tests inside the container:
```bash
make test-grpc-unit
```

## Getting an API Key 

<https://documentation.five9.com/bundle/studio-combo/page/studio-manage/topics/api-keys.htm>
