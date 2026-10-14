# Copyright 2026 Google LLC
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

set -e

if [ -f .env ]; then
  source .env
else
  echo "Error: .env file not found." >&2
  exit 1
fi

if [ -z "$SERVICE_REGION" ]; then
  echo "Error: SERVICE_REGION is not set. Check your .env file." >&2
  exit 1
fi


echo $SERVICE_REGION
echo $GCP_PROJECT_ID
echo $VOICE_INTERCEPTOR_SERVICE
gcloud config set project $GCP_PROJECT_ID
# Find the redis port and redis IP address by instance id
export REDISHOST=`gcloud redis instances describe $REDIS_INSTANCE_ID --region $SERVICE_REGION --format 'value(host)'`
export REDISPORT=`gcloud redis instances describe $REDIS_INSTANCE_ID --region $SERVICE_REGION --format 'value(port)'`

echo $REDISHOST
echo $REDISPORT

# create service account for audiohook connector
service_account="$SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
echo $service_account
if [[ "$service_account" = \
  `gcloud iam service-accounts list --filter=$service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $service_account as it exists."
else
  gcloud iam service-accounts create $SERVICE_ACCOUNT \
  --description='Genesys cloud audiohook interceptor service account, have dialogflow API access' \
  --display-name='Genesys cloud audiohook interceptor service account'
fi

# Add necessary IAM roles for UI Connector service account.
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$service_account" \
  --role='roles/redis.editor' \
  --condition="None"
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$service_account" \
  --role='roles/vpcaccess.user' \
  --condition="None"
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$service_account" \
  --role='roles/compute.viewer' \
  --condition="None"
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$service_account" \
  --role='roles/dialogflow.agentAssistClient' \
  --condition="None"


# Cloud Run settings for long-lived Audiohook websockets:
# --timeout 3600: Cloud Run request timeout (maximum). Each call is one
#   websocket request, so this is the maximum call duration.
# --concurrency 8: maximum calls per instance. Must be lower than the gunicorn
#   thread count (GUNICORN_THREADS=10 in the Dockerfile) so that every routed
#   call gets a thread and 2 threads stay free for the liveness probe.
# --no-cpu-throttling: the streaming threads keep sending audio to Dialogflow
#   between websocket messages, so CPU must stay allocated.
# --liveness-probe on /healthz: served by the gunicorn worker, so Cloud Run
#   restarts the instance if the worker stops accepting connections. A TCP
#   probe cannot detect this because the gunicorn master keeps the port open.
#   Paused or silent calls do not affect the probe.
gcloud run deploy $VOICE_INTERCEPTOR_SERVICE\
  --source . \
  --platform managed \
  --service-account=$service_account \
  --port 443 \
  --min-instances=1 \
  --allow-unauthenticated \
  --vpc-connector=$VPC_CONNECTOR_NAME  \
  --timeout 3600 \
  --concurrency 8 \
  --no-cpu-throttling \
  --liveness-probe=httpGet.path=/healthz,periodSeconds=10,timeoutSeconds=5,failureThreshold=3 \
  --region $CLOUD_RUN_SERVICE_REGION \
  --set-env-vars GCP_PROJECT_ID=$GCP_PROJECT_ID \
  --set-env-vars SERVICE_REGION=$SERVICE_REGION \
  --set-env-vars CONVERSATION_PROFILE_NAME=$CONVERSATION_PROFILE_NAME \
  --set-env-vars API_KEY=$API_KEY \
  --set-env-vars UI_CONNECTOR=$UI_CONNECTOR \
  --set-env-vars REDISPORT=$REDISPORT \
  --set-env-vars REDISHOST=$REDISHOST