# GenesysCloud Voice Integration

[Genesys Cloud Voice Integration Guide](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)

## Authentication & Security (Progressive Enhancement)

The AudioHook WebSocket interceptor supports optional authentication and RFC 9421 HMAC-SHA256 signature verification during the WebSocket handshake (`/connect`):

| Variable | Description | Mode |
| :--- | :--- | :--- |
| `API_KEY` (or `AUDIOHOOK_API_KEY`) | Shared API key validated against `X-API-KEY` header. | Optional |
| `CLIENT_SECRET` (or `AUDIOHOOK_CLIENT_SECRET`) | Base64-encoded client secret used to verify RFC 9421 HMAC-SHA256 signatures (`Signature-Input` / `Signature`). | Optional |

* **Unauthenticated Mode (Default)**: If neither `API_KEY` nor `CLIENT_SECRET` is set, the service accepts incoming WebSocket connections without rejecting requests, preserving full backward compatibility.
* **Hardened Mode**: When `CLIENT_SECRET` is configured, incoming handshakes must include valid RFC 9421 HTTP Message Signatures computed over request components (`@request-target`, `audiohook-*`, `x-api-key`). Unauthorized or forged requests are rejected with WebSocket close code `1008 (Policy Violation)`.

