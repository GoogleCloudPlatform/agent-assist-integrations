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


# Simple solution for extracting secrets and vars from the GitHub environment
# and setting them all as environment variables for the setup scripts to use
# This allows passing of secrets to env files as defined in .env.example
# https://stackoverflow.com/a/75789640

# Create string to use as a delimiter
EOF=_PS_TEMPLATE_VAR_EOF_

# Outputs the name/value pairs in the required format for multiline strings
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-strings
to_envs() { jq -r "to_entries[] | \"\(.key)<<$EOF\n\(.value)\n$EOF\n\""; }

# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable
[[ -n "$VARS_CONTEXT" ]] && echo "$VARS_CONTEXT" | to_envs >> $GITHUB_ENV
echo "$SECRETS_CONTEXT" | to_envs >> $GITHUB_ENV