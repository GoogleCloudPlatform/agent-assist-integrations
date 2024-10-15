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

# Please update the following parameters before running the script
export GCP_PROJECT_ID='your-project-id'
export AA_MODULE_APPLICATION_SERVER="your-ui-module"
export CONVERSATION_PROFILE='your-conversation-profile'
export FEATURES='your-features-list'
export UI_MODULE_SERVICE_ACCOUNT="your-ui-module-aa"
export OAUTH_CLIENT_ID="your-oauth-client-id"
export GENESYS_CLOUD_REGION="mypurecloud.com"
export GENESYS_CLOUD_ENVIORNMENT="prod"
export APPLICATION_SERVER_URL="your-aa-application-url"
export PROXY_SERVER="your-proxy-server-url"
gcloud config set project $GCP_PROJECT_ID

ui_module_service_account="$UI_MODULE_SERVICE_ACCOUNT@$GCP_PROJECT_ID.iam.gserviceaccount.com"
if [[ "$ui_module_service_account" = \
  `gcloud iam service-accounts list --filter=$ui_module_service_account --format='value(EMAIL)'` ]]; then
  echo "Skip creating service account $ui_module_service_account as it exists."
else
  gcloud iam service-accounts create $UI_MODULE_SERVICE_ACCOUNT \
    --display-name "UI Module Web Application Service Account"
fi


# Deploy the gcloud run region.
# PROXY_SERVER should be the service that runs ui-connector
gcloud run deploy $AA_MODULE_APPLICATION_SERVER \
--source . \
--service-account=$ui_module_service_account \
--memory 1Gi --platform managed \
--region us-central1 \
--allow-unauthenticated \
--set-env-vars ^~^OAUTH_CLIENT_ID=$OAUTH_CLIENT_ID~GENESYS_CLOUD_REGION=$GENESYS_CLOUD_REGION~GENESYS_CLOUD_ENVIORNMENT=$GENESYS_CLOUD_ENVIORNMENT~CONVERSATION_PROFILE=$CONVERSATION_PROFILE~FEATURES=$FEATURES~PROJECT_ID=$GCP_PROJECT_ID~PROXY_SERVER=$PROXY_SERVER~APPLICATION_SERVER_URL=$APPLICATION_SERVER_URL

export APPLICATION_SERVER_URL=$(gcloud run services describe $AA_MODULE_APPLICATION_SERVER --region us-central1 --format 'value(status.url)')

# Update the application sverver url for cloud run service
gcloud run deploy $AA_MODULE_APPLICATION_SERVER \
--source . \
--service-account=$ui_module_service_account \
--memory 1Gi --platform managed \
--region us-central1 \
--allow-unauthenticated \
--set-env-vars ^~^OAUTH_CLIENT_ID=$OAUTH_CLIENT_ID~GENESYS_CLOUD_REGION=$GENESYS_CLOUD_REGION~GENESYS_CLOUD_ENVIORNMENT=$GENESYS_CLOUD_ENVIORNMENT~CONVERSATION_PROFILE=$CONVERSATION_PROFILE~FEATURES=$FEATURES~PROJECT_ID=$GCP_PROJECT_ID~PROXY_SERVER=$PROXY_SERVER~APPLICATION_SERVER_URL=$APPLICATION_SERVER_URL
