# GenesysCloud Voice Integration

[Genesys Cloud Voice Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)

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
