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

# This script will push the Terraform State to a Twilio Function as an asset.
set -e
source ./config.sh
project_name=$tfstate_service_name

echo "Trying to Export Terraform State for $ENVIRONMENT"
IFS="|" read -ra tf_state_files <<<"$TF_STATE_FILES"

mkdir -p $project_name/assets
mkdir -p $project_name/functions

for item in "${tf_state_files[@]}"; do
	directory="../terraform/environments/default/$item"
	if [ -f "./$directory" ]; then
		echo "$item present, uploading"
		openssl enc -in "$directory" -aes-256-cbc -pbkdf2 -k "$ENCRYPTION_KEY$tfstate_version" -out "./$item.enc"
		tar -czvf "./$item.tar.private.gz" "./$item.enc"
		mv "./$item.tar.private.gz" "./$project_name/assets/"
		rm -f "./$item.enc"
	else
		echo "$item missing, skipping upload..."
	fi
done

# We need a package.json with the project name to use the serverless: deploy command.
package_json=$(
	cat <<EOL
{"name":"$project_name", "dependencies":{"twilio":"3.56","@twilio/runtime-handler":"1.3.0"}}
EOL
)

verify_function=$(cat ./verify-signature.js)

echo "$package_json" >./$project_name/package.json
echo "$verify_function" >./$project_name/functions/verify-function.js

npx twilio serverless:deploy --assets --production --override-existing-project --cwd="./$project_name"
rm -rf $project_name
