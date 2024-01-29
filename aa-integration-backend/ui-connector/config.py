# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging

# The id of the GCP project where Cloud Run services are deployed on.
GCP_PROJECT_ID = os.environ['GCP_PROJECT_ID']

# Set up the connection with Redis database
REDIS_HOST = os.environ.get('REDISHOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDISPORT', 6379))

# Cloud run could recognize logging files under '/var/log/' folder
logging.basicConfig(filename=os.environ.get(
    'LOGGING_FILE', '/var/log/test.log'), level=logging.INFO)
# Comment this line for local test
# logging.basicConfig(level=logging.DEBUG)

# The path to a jwt secret key file. It is specified when mounting the secret key
# stored in SecretManager to Cloud Run service as a volume.
# Reference: https://cloud.google.com/run/docs/configuring/secrets#mounting-secrets.
JWT_SECRET_KEY_PATH = '/secret/jwt_secret_key'

# TODO replace '*' with a list of allowed origins to limit the access to your server.
# Origin or list of origins that are allowed to connect to this server.
CORS_ALLOWED_ORIGINS = '*'

# Lifetime for generated JWT
JWT_TOKEN_LIFETIME = 60  # minutes