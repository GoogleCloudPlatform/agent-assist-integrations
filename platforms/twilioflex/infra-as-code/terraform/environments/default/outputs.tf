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

# these aren't used for anything other than debug output within the CI workflow.

# FEATURE: remove-all
output "template_example_assign_to_anyone_workflow_sid" {
  value = twilio_taskrouter_workspaces_workflows_v1.template_example_assign_to_anyone.sid
  description = "Template example assign to anyone workflow SID"
}
# END FEATURE: remove-all





