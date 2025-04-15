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

if [[ $1 == 'generate-static-resources' ]]; then
  # UI Modules Javascript
  # https://cloud.google.com/agent-assist/docs/ui-modules#agent-assist-features
  # Uncomment below to download JS for individual UI Modules

  for file in container transcript # summarization smart_reply knowledge_assist
  do
    dir_path=force-app/main/default/staticresources/ui_modules
    file_path=${dir_path}/${file}.js
    mkdir -p ${dir_path}
    rm -f ${file_path} # delete file if exists
    rm -f ${file_path}.resource-meta.xml # delete file if exists
    curl --silent https://www.gstatic.com/agent-assist-ui-modules/latest/${file}.js > $file_path
    echo downloaded js and wrote ${file_path}
  done
  sf static-resource generate \
    --name ui_modules \
    --output-dir force-app/main/default/staticresources \
    --type application/zip

  # UI Modules - Knowledge Assist (not GKA) Javascript
  # https://cloud.google.com/agent-assist/docs/ui-modules-knowledge-assist-documentation
  # Uncomment below to download JS for Knowledge Assist (non-generative version)
  # file=knowledge_assist_v1
  # file_path=force-app/main/default/staticresources/${file}.js
  # rm --force $file_path # delete file if exists
  # rm --force $file_path.resource-meta.xml # delete file if exists
  # sf static-resource generate \
  #     --name ${file} \
  #     --output-dir force-app/main/default/staticresources \
  #     --type application/javascript
  # curl --silent https://www.gstatic.com/agent-assist-ui-modules/v1/knowledge_assist.js > $file_path # Note the version - this is KA, not GKA.
  # echo downloaded js and wrote $file_path

  # Socket.IO - https://unpkg.com/socket.io-client@4.8.1/dist/socket.io.min.js
  # Uncomment below to add the Socket.IO client as a static resource.
  file=socketio
  file_path=force-app/main/default/staticresources/${file}.js
  rm --force $file_path # delete file if exists
  rm --force $file_path.resource-meta.xml # delete file if exists
  sf static-resource generate \
      --name ${file} \
      --output-dir force-app/main/default/staticresources \
      --type application/javascript
  curl --silent https://unpkg.com/socket.io-client@4.8.1/dist/socket.io.min.js > $file_path
  echo downloaded js and wrote $file_path

  # SVG Files
  # Place .svg files in the staticresources directory, then...
  for file in $(ls force-app/main/default/staticresources/ | grep -E 'svg'); do
    file=$(echo ${file} | cut -d . -f 1)
    sf static-resource generate \
        --name ${file} \
        --output-dir force-app/main/default/staticresources \
        --type image/svg+xml
    rm force-app/main/default/staticresources/${file}.resource # don't need, file exists
  done
  # Add file types as needed (or dynamically assign MIME by extension), e.g.
  # file=large-css-file
  # file_path=force-app/main/default/staticresources/$file.css
  # sf static-resource generate \
  #     --name $file \
  #     --output-dir force-app/main/default/staticresources \
  #     --type text/css
  # curl --silent https://www.gstatic.com/path/to/${file}.css > $file_path

elif [[ $1 == 'login-devhub' ]]; then
  printf "Enter your Developer Edition email from\nhttps://trailhead.salesforce.com/users/profiles/orgs: "
  read DEV_EMAIL
  INSTANCE_URL=https://$(echo ${DEV_EMAIL} | cut -f 2 -d @ | cut -f 1 -d .)-dev-ed.trailblaze.my.salesforce.com
  echo "Log in using access code and browser..."
  sf org login device --set-default-dev-hub --alias DevHub --instance-url=${INSTANCE_URL}

elif [[ $1 == 'setup-scratch' ]]; then
  sf org create scratch \
    --edition developer \
    --set-default \
    --definition-file scratch-def.json \
    --alias scratch
  sf org generate password --target-org scratch > /dev/null 2>&1
  sf org display user --target-org scratch 2> /dev/null | grep -E 'Username|Login|Password'

elif [[ $1 == 'deploy-scratch' ]]; then
  sf project deploy start --target-org scratch

elif [[ $1 == 'teardown-scratch' ]]; then
  sf org delete scratch --target-org scratch

else
  echo 'setup.sh takes one argument (one of generate-static-resources, login-devhub, setup-scratch, teardown-scratch)'
fi
