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

# Source the .env file
source .env
cloud_run_service=run.googleapis.com
cloud_build_service=cloudbuild.googleapis.com


# Make a copy of the .env.example file and name it to .env then update the
# variables inside it
gcloud config set project $GCP_PROJECT_ID

# Create a service account for the web application.
# Check if cloud run service is already enabled
if [[ "$cloud_run_service" = \
  `gcloud services list --enabled --filter=$cloud_run_service --format='value(NAME)'` ]]; then
  echo "Skip enable cloud run API as it exists."
else
  gcloud services enable $cloud_run_service
fi
# Check if cloud build service is already enabled
if [[ "$cloud_build_service" = \
  `gcloud services list --enabled --filter=$cloud_build_service --format='value(NAME)'` ]]; then
  echo "Skip enable cloud build API as it exists."
else
  gcloud services enable $cloud_build_service
fi

# Create a service account for the web application.
ui_module_service_account="$UI_MODULE_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if [[ "$ui_module_service_account" = \
  `gcloud iam service-accounts list --filter=$ui_module_service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $ui_module_service_account as it exists."
else
  gcloud iam service-accounts create $UI_MODULE_SERVICE_ACCOUNT \
    --display-name "UI Module Web Application Service Account"
fi

# Assign the service account dialogflow client role.
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$ui_module_service_account" \
  --role='roles/dialogflow.client' \
  --condition=None

# Deploy the gcloud run region.
# PROXY_SERVER should be the service that runs ui-connector
gcloud run deploy $AA_MODULE_APPLICATION_SERVER \
--source . \
--service-account=$ui_module_service_account \
--memory 1Gi --platform managed \
--region us-central1 \
--allow-unauthenticated \
--set-env-vars ^~^OAUTH_CLIENT_ID=$OAUTH_CLIENT_ID~GENESYS_CLOUD_REGION=$GENESYS_CLOUD_REGION~GENESYS_CLOUD_ENVIORNMENT=$GENESYS_CLOUD_ENVIORNMENT~CONVERSATION_PROFILE=$CONVERSATION_PROFILE~FEATURES=$FEATURES~PROJECT_ID=$GCP_PROJECT_ID~PROXY_SERVER=$PROXY_SERVER~APPLICATION_SERVER_URL=$APPLICATION_SERVER_URL~CHANNEL=$CHANNEL

export APPLICATION_SERVER_URL=$(gcloud run services describe $AA_MODULE_APPLICATION_SERVER --region us-central1 --format 'value(status.url)')

# Update the application sverver url for cloud run service
gcloud run deploy $AA_MODULE_APPLICATION_SERVER \
--source . \
--service-account=$ui_module_service_account \
--memory 1Gi --platform managed \
--region us-central1 \
--allow-unauthenticated \
--set-env-vars ^~^OAUTH_CLIENT_ID=$OAUTH_CLIENT_ID~GENESYS_CLOUD_REGION=$GENESYS_CLOUD_REGION~GENESYS_CLOUD_ENVIORNMENT=$GENESYS_CLOUD_ENVIORNMENT~CONVERSATION_PROFILE=$CONVERSATION_PROFILE~FEATURES=$FEATURES~PROJECT_ID=$GCP_PROJECT_ID~PROXY_SERVER=$PROXY_SERVER~APPLICATION_SERVER_URL=$APPLICATION_SERVER_URL~CHANNEL=$CHANNEL
