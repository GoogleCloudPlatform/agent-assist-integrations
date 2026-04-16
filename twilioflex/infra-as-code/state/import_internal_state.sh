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

# This script will import the project workflows, queues, channels, activities, and flows for the first time and apply them with Terraform.
set -e

terraform -chdir="../terraform/environments/default" init -input=false

get_value_from_json() {
	input_json="$1"
	key="$2"
	value="$3"
	property="$4"

	filtered_output=$(echo "$input_json" | jq --arg key "$key" --arg value "$value" '.[] | select(.[$key] == $value) // empty' | jq -r ".$property// \"\"")
	echo "$filtered_output"

}

import_resource() {
	input_json="$1"
	name="$2"
	resource="$3"
	key="$4"
	has_sid=${5:-true}

	result=$(get_value_from_json "$input_json" "$key" "$name" "sid")
	if [ -n "$result" ]; then
		if $has_sid; then
			terraform -chdir="../terraform/environments/default" import -input=false -var-file="${ENVIRONMENT:-local}.tfvars" "$resource" "$TF_WORKSPACE_SID"/"$result" || exit
		else
			terraform -chdir="../terraform/environments/default" import -input=false -var-file="${ENVIRONMENT:-local}.tfvars" "$resource" "$result" || exit
		fi
	fi

}

importInternalState() {
	echo " - Discovering and importing existing Twilio state for known definitions into a new terraform state file" >>$GITHUB_STEP_SUMMARY
	TF_WORKSPACE_SID=$(cat "../terraform/environments/default/${ENVIRONMENT:-local}.tfvars" | grep "TWILIO_FLEX_WORKSPACE_SID" | sed 's/ = /=/;s/^\([^ ]*\)="\([^"].*\)"/\2/')

	workflows=$(npx twilio api:taskrouter:v1:workspaces:workflows:list --workspace-sid "$TF_WORKSPACE_SID" --no-limit -o json | jq 'map(del(.configuration))')
	queues=$(npx twilio api:taskrouter:v1:workspaces:task-queues:list --workspace-sid "$TF_WORKSPACE_SID" --no-limit -o json)
	channels=$(npx twilio api:taskrouter:v1:workspaces:task-channels:list --workspace-sid "$TF_WORKSPACE_SID" --no-limit -o json)
	activities=$(npx twilio api:taskrouter:v1:workspaces:activities:list --workspace-sid "$TF_WORKSPACE_SID" --no-limit -o json)
	flows=$(npx twilio api:studio:v2:flows:list --no-limit -o json)

# FEATURE: remove-all
	import_resource "$workflows" "Template Example Assign to Anyone" "twilio_taskrouter_workspaces_workflows_v1.template_example_assign_to_anyone" "friendlyName"
	import_resource "$queues" "Template Example Everyone" "twilio_taskrouter_workspaces_task_queues_v1.template_example_everyone" "friendlyName"
	import_resource "$queues" "Template Example Sales" "twilio_taskrouter_workspaces_task_queues_v1.template_example_sales" "friendlyName"
	import_resource "$queues" "Template Example Support" "twilio_taskrouter_workspaces_task_queues_v1.template_example_support" "friendlyName"
	import_resource "$channels" "voice" "twilio_taskrouter_workspaces_task_channels_v1.voice" "uniqueName"
	echo "   - :white_check_mark: Example TaskRouter resources" >>$GITHUB_STEP_SUMMARY
# END FEATURE: remove-all






}

# populate tfvars
(cd ../.. && npm run postinstall -- --skip-packages --files=infra-as-code/terraform/environments/default/example.tfvars)

### only if existing state file does not exist
### do we want to import the internal state
if ! [ -f ../terraform/environments/default/terraform.tfstate ]; then
  importInternalState
fi

terraform -chdir="../terraform/environments/default" apply -input=false -auto-approve -var-file="${ENVIRONMENT:-local}.tfvars"
echo " - Applying terraform configuration complete" >>$GITHUB_STEP_SUMMARY
echo "JOB_FAILED=false" >>"$GITHUB_OUTPUT"
