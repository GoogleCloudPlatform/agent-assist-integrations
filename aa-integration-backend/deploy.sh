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
#
# A script for Agent Assist Backend Module deployment. Estimation: 10min.
# Please update the value of environment variables as necessary before running the script.
#
# Prerequisites:
#     1. Install Google Cloud CLI (https://cloud.google.com/sdk/docs/install-sdk) or use Google Cloud Shell for script execution.
#     2. Create your conversation profile and configure it with desired Cloud Pub/Sub notifications.
#       - How to create a conversation profile: https://cloud.google.com/agent-assist/docs/conversation-profile
#       - How to enable Cloud Pub/Sub notifications: https://cloud.google.com/agent-assist/docs/pub-sub
#     3. Make sure your account has Owner permissions in your GCP project or been granted the following IAM roles.
#       - Project IAM Admin (roles/resourcemanager.projectIamAdmin)
#       - Service Usage Admin (roles/serviceusage.serviceUsageAdmin)
#       - Service Account Admin (roles/iam.serviceAccountAdmin)
#       - Service Account User (roles/iam.serviceAccountUser)
#       - Pub/Sub Admin (roles/pubsub.admin)
#       - Secret Manager Admin (roles/secretmanager.admin)
#       - Cloud Build Editor (roles/cloudbuild.builds.editor)
#       - Artifact Registry Administrator (roles/artifactregistry.admin)
#       - Storage Admin (roles/storage.admin)
#       - Cloud Run Admin (roles/run.admin)
#       - Cloud Memorystore Redis Admin (roles/redis.admin)
#       - Serverless VPC Access Admin (roles/vpcaccess.admin)
#     4. Customize authentication method by modifying `auth.check_auth()` method under folder `/ui-connector`.
#
# How to run this script:
#     cd aa-integration-backend/ && sh ./deploy.sh


# TODO: Please update the following fields according to your existing resources.
export GCP_PROJECT_ID='your-project-id'
export ADMIN_ACCOUNT='your-admin-account'
export AGENT_ASSIST_NOTIFICATIONS_TOPIC_ID='aa-new-suggestion-topic'
export NEW_MESSAGE_NOTIFICATIONS_TOPIC_ID='aa-new-message-topic'
export CONVERSATION_LIFECYCLE_NOTIFICATIONS_TOPIC_ID='aa-conversation-event-topic'

# TODO: Check the secret key you plan to use.
# We recommend generating a random hash as the JWT secret key so that it cannot be guessed by attackers.
export JWT_SECRET_KEY=`echo $RANDOM | md5sum | head -c 20;`

# The region where your resources will be located at.
export SERVICE_REGION='us-central1'

# The name of your JWT secret.
export JWT_SECRET_NAME='aa-integration-jwt-secret'

# Configurations for Memorystore for Redis.
export VPC_CONNECTOR_NAME='aa-integration-vpc'
export VPC_NETWORK='default'
export REDIS_IP_RANGE='10.8.0.0/28'
export REDIS_INSTANCE_ID='aa-integration-redis'

# Configurations for Cloud Run services.
export CONNECTOR_SERVICE_ACCOUNT_NAME='ui-connector'
export INTERCEPTOR_SERVICE_ACCOUNT_NAME='cloud-pubsub-interceptor'
export CONNECTOR_SERVICE_NAME='ui-connector'
export INTERCEPTOR_SERVICE_NAME='cloud-pubsub-interceptor'

# Configurations for Cloud Pub/Sub topics and subscriptions.
export CLOUD_RUN_PUBSUB_INVOKER_NAME='cloud-run-pubsub-invoker'
export AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID='aa-new-suggestion-sub'
export NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID='aa-new-message-sub'
export CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID='aa-conversation-event-sub'


echo -e "\n\n ==================== Set up Google Cloud CLI Configurations =================== \n\n"

# Set the project of your gcloud config.
gcloud config set project $GCP_PROJECT_ID

# Set the account of your gcloud config.
gcloud config set account $ADMIN_ACCOUNT


echo -e "\n\n ============================= Enable GCP Services ============================= \n\n"

# Enable the Dialogflow API.
gcloud services enable dialogflow.googleapis.com

# Enable the Cloud Pub/Sub API.
gcloud services enable pubsub.googleapis.com

# Enable the Cloud Run Admin API.
gcloud services enable run.googleapis.com

# Enable the Secret Manager API.
gcloud services enable secretmanager.googleapis.com

# Enable the Compute Engine API.
gcloud services enable compute.googleapis.com

# Enable the Serverless VPC Access API.
gcloud services enable vpcaccess.googleapis.com

# Enable the Google Cloud Memorystore for Redis API.
gcloud services enable redis.googleapis.com


echo -e '\n\n =========================== Create Service Accounts =========================== \n\n'

# Create service account for UI Connector service runtime.
connector_service_account="$CONNECTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if [[ "$connector_service_account" = \
  `gcloud iam service-accounts list --filter=$connector_service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $connector_service_account as it exists."
else
  gcloud iam service-accounts create $CONNECTOR_SERVICE_ACCOUNT_NAME \
  --description='Agent Assist integration - UI connector service account' \
  --display-name='Agent Assist integration - UI connector'
fi

# Add necessary IAM roles for UI Connector service account.
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$connector_service_account" \
  --role='roles/redis.editor'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$connector_service_account" \
  --role='roles/vpcaccess.user'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$connector_service_account" \
  --role='roles/compute.viewer'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$connector_service_account" \
  --role='roles/secretmanager.secretAccessor'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$connector_service_account" \
  --role='roles/dialogflow.agentAssistClient'

# Create service account for Cloud Pub/Sub Interceptor service runtime.
interceptor_service_account="$INTERCEPTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if [[ "$interceptor_service_account" = \
  `gcloud iam service-accounts list --filter=$interceptor_service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $interceptor_service_account as it exists."
else
  gcloud iam service-accounts create $INTERCEPTOR_SERVICE_ACCOUNT_NAME \
    --description='Agent Assist integration - Pubsub interceptor service account' \
    --display-name='Agent Assist integration - Pubsub interceptor'
fi

# Add necessary IAM roles for Cloud Pub/Sub Interceptor service account.
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$interceptor_service_account" \
  --role='roles/redis.editor'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$interceptor_service_account" \
  --role='roles/vpcaccess.user'
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$interceptor_service_account" \
  --role='roles/compute.viewer'


echo -e '\n\n ===================== Create a JWT Secret Key ===================== \n\n'

# Create or update a JWT secret key.
if [[ $JWT_SECRET_NAME = `gcloud secrets list --filter=$JWT_SECRET_NAME --format='value(NAME)'` ]]; then
  printf $JWT_SECRET_KEY | gcloud secrets versions add $JWT_SECRET_NAME --data-file=-
else
  printf $JWT_SECRET_KEY | \
  gcloud secrets create $JWT_SECRET_NAME \
    --data-file=-
    --replication-policy=user-managed
    --locations=$SERVICE_REGION
fi


echo -e '\n\n ========================= Setup Memorystore for Redis ========================= \n\n'

# Create a Redis instance in the same region as your Cloud Run services.
if [[ "$REDIS_INSTANCE_ID" = \
  `gcloud redis instances list --region=$SERVICE_REGION \
    --filter=$REDIS_INSTANCE_ID --format='value(INSTANCE_NAME)'` ]]; then
  echo "Skip creating redis instance $REDIS_INSTANCE_ID as it exists."
else
  gcloud redis instances create $REDIS_INSTANCE_ID --size=5 --region=$SERVICE_REGION --format=json
fi

# Create a Serverless VPC Access connector with a custom IP range.
if [[ $VPC_CONNECTOR_NAME = \
  `gcloud compute networks vpc-access connectors list --region=$SERVICE_REGION \
    --filter=$VPC_CONNECTOR_NAME --format='value(CONNECTOR_ID)'` ]]; then
  echo "Skip creating Serverless VPC Access connector $VPC_CONNECTOR_NAME as it exists."
else
  gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
    --network $VPC_NETWORK \
    --region $SERVICE_REGION \
    --range $REDIS_IP_RANGE \
    --format=json
fi

# Record redis instance information for later service deployment.
export REDIS_HOST=`gcloud redis instances describe $REDIS_INSTANCE_ID --region $SERVICE_REGION --format 'value(host)'`
export REDIS_PORT=`gcloud redis instances describe $REDIS_INSTANCE_ID --region $SERVICE_REGION --format 'value(port)'`


echo -e '\n\n ========================= Deploy UI Connector Service ========================= \n\n'

# Deploy UI Connector Cloud Run service.
gcloud run deploy $CONNECTOR_SERVICE_NAME \
  --source ./ui-connector \
  --platform managed \
  --service-account=$CONNECTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --timeout 3600 \
  --region $SERVICE_REGION \
  --vpc-connector $VPC_CONNECTOR_NAME \
  --min-instances=1 \
  --set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT,GCP_PROJECT_ID=$GCP_PROJECT_ID \
  --update-secrets=/secret/jwt_secret_key=${JWT_SECRET_NAME}:latest


echo -e '\n\n =================== Deploy Cloud PubSub Interceptor Service =================== \n\n'

# Deploy Cloud PubSub Interceptor Cloud Run service.
gcloud run deploy $INTERCEPTOR_SERVICE_NAME \
  --source ./cloud-pubsub-interceptor \
  --platform managed \
  --service-account=$INTERCEPTOR_SERVICE_ACCOUNT_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --region $SERVICE_REGION \
  --vpc-connector $VPC_CONNECTOR_NAME \
  --ingress=internal \
  --min-instances=1 \
  --set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT


echo -e '\n\n ================= Configure Cloud PubSub Topic Subscriptions ================== \n\n'

# Create a service account to represent the Pub/Sub subscription identity.
pubsub_service_account="$CLOUD_RUN_PUBSUB_INVOKER_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if [[ "$pubsub_service_account" = \
  `gcloud iam service-accounts list --filter=$pubsub_service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $pubsub_service_account as it exists."
else
  gcloud iam service-accounts create $CLOUD_RUN_PUBSUB_INVOKER_NAME \
    --display-name "Cloud Run Pub/Sub Invoker"
fi

# Give the service account permission to invoke your interceptor service.
gcloud run services add-iam-policy-binding $INTERCEPTOR_SERVICE_NAME \
  --member=serviceAccount:$pubsub_service_account \
  --role=roles/run.invoker \
  --region=$SERVICE_REGION

# Get the URL of deployed Cloud PubSub Interceptor Service.
interceptor_service_info=`gcloud run services describe $INTERCEPTOR_SERVICE_NAME --region $SERVICE_REGION`
interceptor_service_url=`echo $interceptor_service_info | head -4 | cut -d' ' -f 8`

# Create a subscription for the Pub/Sub topic you configured for new suggestions.
new_suggestion_sub_name="projects/$GCP_PROJECT_ID/subscriptions/$AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID"
if [[ "$new_suggestion_sub_name" = \
  `gcloud pubsub subscriptions list --filter=$new_suggestion_sub_name --format='value(name)'` ]]; then
  gcloud pubsub subscriptions update $AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/human-agent-assistant-event \
    --push-auth-service-account=$pubsub_service_account
else
  gcloud pubsub subscriptions create $AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID \
    --topic $AGENT_ASSIST_NOTIFICATIONS_TOPIC_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/human-agent-assistant-event \
    --push-auth-service-account=$pubsub_service_account
fi

# Create a subscription for the Pub/Sub topic you configured for new message events.
new_message_sub_name="projects/$GCP_PROJECT_ID/subscriptions/$NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID"
if [[ "$new_message_sub_name" = \
  `gcloud pubsub subscriptions list --filter=$new_message_sub_name --format='value(name)'` ]]; then
  gcloud pubsub subscriptions update $NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/new-message-event \
    --push-auth-service-account=$pubsub_service_account
else
  gcloud pubsub subscriptions create $NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID \
    --topic $NEW_MESSAGE_NOTIFICATIONS_TOPIC_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/new-message-event \
    --push-auth-service-account=$pubsub_service_account
fi

# Create a subscription for the Pub/Sub topic you configured for conversation lifecycle events.
conversation_event_sub_name="projects/$GCP_PROJECT_ID/subscriptions/$CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID"
if [[ "$conversation_event_sub_name" = \
  `gcloud pubsub subscriptions list --filter=$conversation_event_sub_name --format='value(name)'` ]]; then
  gcloud pubsub subscriptions update $CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/conversation-lifecycle-event \
    --push-auth-service-account=$pubsub_service_account
else
  gcloud pubsub subscriptions create $CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID \
    --topic $CONVERSATION_LIFECYCLE_NOTIFICATIONS_TOPIC_ID \
    --expiration-period=never \
    --push-endpoint=$interceptor_service_url/conversation-lifecycle-event \
    --push-auth-service-account=$pubsub_service_account
fi


echo -e '\n\n =============================================================================== \n\n'

echo 'Deployment completed. Visit this URL of your UI Connector Cloud Run Service for a chat demo.'

ui_connector_service_info=`gcloud run services describe $CONNECTOR_SERVICE_NAME --region $SERVICE_REGION`
echo $ui_connector_service_info | head -4 | cut -d' ' -f 8

echo -e '\n\n =============================================================================== \n\n'