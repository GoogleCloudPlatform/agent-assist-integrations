# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.12-slim

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME

# Copy dependencies first for better caching
COPY requirements.txt ./

# Install production dependencies.
RUN pip install -r requirements.txt

COPY . ./

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and GUNICORN_THREADS threads.
#
# GUNICORN_THREADS: each Audiohook websocket holds one gunicorn thread for the
# whole call, so GUNICORN_THREADS must be greater than the Cloud Run
# concurrency set in deploy.sh (concurrency 8 + 2 spare threads for the
# /healthz liveness probe = 10). If concurrency is higher than the thread
# count, Cloud Run routes new calls to an instance that has no free thread and
# they hang until the request timeout.
#
# GUNICORN_TIMEOUT: with the gthread worker this is NOT a per-call or idle
# timeout. It is a heartbeat check on the worker main loop, which notifies the
# gunicorn master about once per second independently of the calls it serves.
# Long calls and long pauses (e.g. the call is paused for minutes while a
# participant looks something up) therefore never trigger it. It only fires
# when the worker main loop itself is dead or stuck, in which case the master
# kills and replaces the worker. Do not set it to 0: that disables the check,
# and a crashed worker would keep the instance alive without serving calls.
# The maximum call duration is controlled by the Cloud Run request timeout
# (--timeout 3600 in deploy.sh), not by this value.
ENV GUNICORN_THREADS=10
ENV GUNICORN_TIMEOUT=60
CMD exec gunicorn --bind :$PORT --workers 1 --threads $GUNICORN_THREADS --timeout $GUNICORN_TIMEOUT main:app
