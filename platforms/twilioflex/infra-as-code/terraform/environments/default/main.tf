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

# FEATURE: remove-all
resource "twilio_taskrouter_workspaces_task_channels_v1" "voice" {
  workspace_sid	= var.TWILIO_FLEX_WORKSPACE_SID
  friendly_name	= "Voice"
  unique_name = "voice"
}
# END FEATURE: remove-all






