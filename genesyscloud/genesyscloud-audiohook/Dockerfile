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
# Each Audiohook websocket holds one gunicorn thread for the whole call, so
# GUNICORN_THREADS must be greater than the Cloud Run concurrency (keep 2
# spare threads for health checks), see deploy.sh.
# --timeout must not be 0: with the gthread worker the heartbeat comes from the
# worker main loop, so long-lived websockets do not trigger it, but a dead or
# stuck worker is killed and replaced by the gunicorn master.
ENV GUNICORN_THREADS=10
ENV GUNICORN_TIMEOUT=60
CMD exec gunicorn --bind :$PORT --workers 1 --threads $GUNICORN_THREADS --timeout $GUNICORN_TIMEOUT main:app
