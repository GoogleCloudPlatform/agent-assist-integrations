#!/bin/bash
# Copyright 2025 Google LLC
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

# This script deletes the assets stored in the Twilio Function.
set -e
echo "Trying to Delete Terraform State for $ENVIRONMENT"

source ./config.sh

tfstate_sid=$(twilio serverless:list services --properties sid,unique_name | awk -v service_name="$tfstate_service_name" '$2==service_name {print $1}')

echo "TF State SID is $tfstate_sid"
echo "TF State service name is $tfstate_service_name"

twilio api:serverless:v1:services:remove --sid $tfstate_sid
