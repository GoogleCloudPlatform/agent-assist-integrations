# Copyright 2024 Google LLC
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

#!/bin/bash

echo -e '\n==============================================================================='
echo "Starting Agent Assist Integration Backend teardown ..."
echo -e '===============================================================================\n'

source ./.env

# Delete service account for UI Connector service runtime.
connector_service_account="$CONNECTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts delete \
  $(gcloud iam service-accounts list \
  --filter=$connector_service_account \
  --format='value(EMAIL)')

# Create service account for Cloud Pub/Sub Interceptor service runtime.
interceptor_service_account="$INTERCEPTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts delete \
  $(gcloud iam service-accounts list \
    --filter=$interceptor_service_account \
    --format='value(EMAIL)')

# Delete the JWT secret and its versions.
gcloud secrets delete \
  $JWT_SECRET_NAME

# Delete a Redis instance in the same region as your Cloud Run services.
gcloud redis instances delete \
  $REDIS_INSTANCE_ID \
  --region=$SERVICE_REGION

# Delete a Serverless VPC Access connector with a custom IP range.
gcloud compute networks vpc-access connectors delete \
  $VPC_CONNECTOR_NAME \
  --region $SERVICE_REGION

# Delete Cloud UI Connector Cloud Run service.
gcloud run services delete \
  $CONNECTOR_SERVICE_NAME

# Delete the images for the Cloud UI Connector Cloud Run service.
IMAGE=$SERVICE_REGION-docker.pkg.dev/$GCP_PROJECT_ID/cloud-run-source-deploy/$CONNECTOR_SERVICE_NAME
gcloud artifacts docker tags delete $IMAGE:latest --quiet
IMAGES=$(gcloud artifacts docker images list \
  $IMAGE \
  --format="value[separator="@"](IMAGE,DIGEST)")
while IFS= read -r line; do
  gcloud artifacts docker images delete $line --quiet
done <<< "$IMAGES"

# Delete Cloud PubSub Interceptor Cloud Run service itself.
gcloud run services delete \
  $INTERCEPTOR_SERVICE_NAME

# Delete the images for the Cloud PubSub Interceptor Cloud Run service.
IMAGE=$SERVICE_REGION-docker.pkg.dev/$GCP_PROJECT_ID/cloud-run-source-deploy/$INTERCEPTOR_SERVICE_NAME
gcloud artifacts docker tags delete $IMAGE:latest --quiet
IMAGES=$(gcloud artifacts docker images list \
  $IMAGE \
  --format="value[separator="@"](IMAGE,DIGEST)")
while IFS= read -r image; do
  gcloud artifacts docker images delete $image --quiet
done <<< "$IMAGES"

# Delete Pub/Sub topics you configured for new suggestions.
gcloud pubsub topics delete \
  $CONVERSATION_LIFECYCLE_NOTIFICATIONS_TOPIC_ID
gcloud pubsub topics delete \
  $NEW_MESSAGE_NOTIFICATIONS_TOPIC_ID
gcloud pubsub topics delete \
  $AGENT_ASSIST_NOTIFICATIONS_TOPIC_ID

# Delete Pub/Sub subscriptions you configured for new suggestions.
gcloud pubsub subscriptions delete \
  $CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID
gcloud pubsub subscriptions delete \
  $NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID
gcloud pubsub subscriptions delete \
  $AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID

# Delete service account to represent the Pub/Sub subscription identity.
pubsub_service_account="$CLOUD_RUN_PUBSUB_INVOKER_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts delete \
  $(gcloud iam service-accounts list \
  --filter=$pubsub_service_account \
  --format='value(EMAIL)')

echo -e '\n==============================================================================='
echo "Agent Assist Integration Backend teardown complete."
echo -e '===============================================================================\n'
