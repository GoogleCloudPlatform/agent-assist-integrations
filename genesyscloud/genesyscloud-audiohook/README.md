# GenesysCloud Voice Integration

[Genesys Cloud Voice Integration Guide](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)

## Authentication & Security

The AudioHook WebSocket interceptor enforces authentication on the WebSocket handshake (`/connect`) via `API_KEY` and/or RFC 9421 HMAC-SHA256 signature verification:

| Variable | Description | Requirement |
| :--- | :--- | :--- |
| `API_KEY` (or `AUDIOHOOK_API_KEY`) | Shared API key validated against `X-API-KEY` header. | At least one of `API_KEY` or `CLIENT_SECRET` required |
| `CLIENT_SECRET` (or `AUDIOHOOK_CLIENT_SECRET`) | Base64-encoded client secret used to verify RFC 9421 HMAC-SHA256 signatures (`Signature-Input` / `Signature`). | Optional (Recommended) |

* **Fail-Closed Enforcement**: If neither `API_KEY` nor `CLIENT_SECRET` is configured, incoming WebSocket connections are rejected with close code `1008 (Policy Violation)`.
* **RFC 9421 Hardened Mode**: When `CLIENT_SECRET` is configured, incoming handshakes must include valid RFC 9421 HTTP Message Signatures computed over request components (`@request-target`, `audiohook-*`, `x-api-key`). Unauthorized or forged requests are rejected with WebSocket close code `1008 (Policy Violation)`.

## Production settings for the Audiohook connector

Each Audiohook websocket holds one gunicorn thread (plus two streaming threads)
for the whole call. When running on Cloud Run:

* **Concurrency must be lower than the gunicorn thread count.** `deploy.sh`
  sets `--concurrency 8` and the container runs 10 threads
  (`GUNICORN_THREADS`), leaving 2 threads for health checks. If concurrency is
  higher than the thread count, Cloud Run keeps routing new calls to an
  instance that cannot serve them, and they hang until the request timeout.
* **Keep a non-zero gunicorn `--timeout`** (`GUNICORN_TIMEOUT`, default 60s).
  The gthread worker heartbeat does not depend on request duration, so long
  calls are not affected, but a dead worker gets replaced.
* **Configure the HTTP liveness probe on `/healthz`.** A TCP probe cannot
  detect a dead gunicorn worker, because the gunicorn master keeps the port
  open.
* Size `--min-instances` / `--max-instances` from the expected number of
  concurrent calls divided by the concurrency, and load test at peak.
