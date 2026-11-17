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
# A script for setting up a voice integration with Dailogflow CX. Estimation: 1min.
# Please update the value of environment variables as necessary before running the script.
#
#
# Prerequisites:
#     1. Install Google Cloud CLI (https://cloud.google.com/sdk/docs/install-sdk) or use Google Cloud Shell for script execution.
#     2. Create your conversation profile and configure it with desired Cloud Pub/Sub notifications.
#       - How to create a conversation profile: https://cloud.google.com/agent-assist/docs/conversation-profile
#       - How to enable Cloud Pub/Sub notifications: https://cloud.google.com/agent-assist/docs/pub-sub
#
# How to run this script:
#     cd aa-integration-backend/ && sh ./voice-setup.sh

curlf() {
  OUTPUT_FILE=$(mktemp)
  HTTP_CODE=$(curl --silent --output $OUTPUT_FILE --write-out "%{http_code}" "$@")
  if [[ ${HTTP_CODE} == 200 ]]; then
    echo '{
            "code": "'$HTTP_CODE'",
            "response": '$(cat $OUTPUT_FILE)'
        }'
  else
    code=`jq '.error.code' $OUTPUT_FILE`
    message=`jq '.error.message' $OUTPUT_FILE`
    echo '{
            "code": "'$code'",
            "message": '$message'
        }'
  fi
  rm $OUTPUT_FILE
}

# Please update the following fields according to your existing resources.
export PROJECT_ID='your-project-id'

# The unique identifier of this conversation profile.
# Format: projects/<Project ID>/locations/<Location ID>/conversationProfiles/<Conversation Profile ID>
export CONVERSATION_PROFILE_NAME='your-conversation-profile-name'

# The canonical id for this location. For example: "us-east1"
export LOCATION_ID='global'

# Set the API_LOCATION_ID_PREFIX if the region is not global
if [[ "$LOCATION_ID" == 'global' ]]; then
    API_LOCATION_ID_PREFIX=""
else
    API_LOCATION_ID_PREFIX="${LOCATION_ID}-"
fi

#Check if the prerequisite commands are installed
echo -e "\n\n ==================== Check for Prerequisite Commands =================== \n\n"
if command -v gcloud &> /dev/null && command -v jq &> /dev/null; then
    echo -e "gcloud and jq are already installed\n"
else
    echo -e "Please install the following packages first, then try again: gcloud jq\n" && exit
fi

echo -e "\n\n ==================== Set up Google Cloud CLI Configurations =================== \n\n"
# Set the project of your gcloud config.
gcloud config set project $PROJECT_ID

#Set JWT for API calls
JWT=`gcloud auth print-access-token`

echo -e "\n\n ============================= Enable GCP Services ============================= \n\n"

dialogflow_api=dialogflow.googleapis.com

if [[ "$dialogflow_api" = \
  `gcloud services list --enabled --filter="Name:$dialogflow_api" --format='value(NAME)'` ]]; then
  echo "Skip enable cloud run API as it exists."
else
  gcloud services enable $dialogflow_api
fi

echo -e "Enabling Dialogflow APIs."
# Enable the Dialogflow API.
gcloud services enable dialogflow.googleapis.com

# Creates an order to request phone numbers be added to a project.
# Request body:
#   phoneNumberSpec: Definition of what is being ordered. Order is for new numbers.
#     count: Total numbers requested, between 1 and 10 inclusive.
#     countryCode: ITU country calling code for the requested numbers. Defaults to 1 (US) until the service is available in other regions.
echo -e "\n\n ======================== Creating Phone Number Order ========================== \n\n"
phone_number_order_response=`curlf -X POST \
                        -H "Authorization: Bearer $JWT" \
                        -H "x-goog-user-project: $PROJECT_ID" \
                        -H "Content-Type: application/json; charset=utf-8" \
                        -d '{
                                "phoneNumberSpec": {
                                    "count": 1,
                                    "countryCode" : 1
                                }
                            }' \
                        https://${API_LOCATION_ID_PREFIX}dialogflow.googleapis.com/v2beta1/projects/$PROJECT_ID/locations/$LOCATION_ID/phoneNumberOrders`

response_code=`echo $phone_number_order_response | jq '.code' | bc`

if [[ $response_code -eq 200 ]]; then
    phone_number_name=`echo $phone_number_order_response | jq -r '.response.phoneNumbers | keys[0]'`
    echo -e "Phone number created."
else
    echo -e "Dialogflow API Error"
    echo -e "Response Code: $response_code"
    echo -e "Error Message: `echo $phone_number_order_response | jq '.message'`"
    exit
fi

# Update the Conversation Profile with the CX Agent and the SIP Config.
# Request body:
#   sipConfig: Configuration for SIP connections.
#     createConversationOnTheFly: Asks Dialogflow Telephony to create the conversation provided in the SIP header on the fly when the call comes in.
# Query parameters:
#   updateMask: The mask to control which fields get updated. This is a comma-separated list of fully qualified names of fields. Example: "user.displayName,photo".
echo -e '\n\n ================= Updating Conversation Profile ================== \n\n'
update_conversation_profile_response=`curlf -X PATCH \
    -H "Authorization: Bearer $JWT" \
    -H "x-goog-user-project: $PROJECT_ID" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d '{
            "sipConfig": {
                "createConversationOnTheFly": true,
            }
        }' \
    https://${API_LOCATION_ID_PREFIX}dialogflow.googleapis.com/v2beta1/${CONVERSATION_PROFILE_NAME}?updateMask=sipConfig.createConversationOnTheFly`

response_code=`echo $update_conversation_profile_response | jq '.code' | bc`
if [[ $response_code -eq 200 ]]; then
    echo -e "Conversation profile updated. Current configuration:"
    echo $update_conversation_profile_response | jq '.response'
else
    echo -e "Dialogflow API Error"
    echo -e "Response Code: $response_code"
    echo -e "Error Message: `echo $update_conversation_profile_response | jq '.message'`"
    exit
fi
# Updates the specified PhoneNumber.
# Request body:
#   conversationProfile: The conversation profile calls to this PhoneNumber should use. The project ID here should be the same as the one in name.
# Query parameters:
#   updateMask: The mask to control which fields get updated. This is a comma-separated list of fully qualified names of fields. Example: "user.displayName,photo".
echo -e '\n\n ================= Associating Phone Number with Conversation Profile ================== \n\n'
associate_phone_number_with_conv_profile_response=`curlf -X PATCH \
                                                        -H "Authorization: Bearer $JWT" \
                                                        -H "x-goog-user-project: $PROJECT_ID" \
                                                        -H "Content-Type: application/json; charset=utf-8" \
                                                        -d '{
                                                                "conversationProfile": "'$CONVERSATION_PROFILE_NAME'"
                                                            }' \
                                                        https://${API_LOCATION_ID_PREFIX}dialogflow.googleapis.com/v2beta1/${phone_number_name}?update_mask=conversationProfile`

response_code=`echo $associate_phone_number_with_conv_profile_response | jq '.code' | bc`
if [[ $response_code -eq 200 ]]; then
    phone_number=`echo $associate_phone_number_with_conv_profile_response | jq '.response.phoneNumber'`
    echo -e "Phone number name: `echo $associate_phone_number_with_conv_profile_response | jq '.response.name'`"
    echo -e "Phone number: ${phone_number:1:2} (${phone_number:3:3}) ${phone_number:6:3}-${phone_number:9:4}"
    echo -e "Conversation Profile name: `echo $associate_phone_number_with_conv_profile_response | jq '.response.conversationProfile'`"
else
    echo -e "Dialogflow API Error"
    echo -e "Response Code: $response_code"
    echo -e "Error Message: `echo $associate_phone_number_with_conv_profile_response | jq '.message'`"
    exit
fi