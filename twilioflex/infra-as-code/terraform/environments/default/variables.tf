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

variable "TWILIO_ACCOUNT_SID" {
  type        = string
  sensitive   = true
  description = "Twilio Account SID"
  validation {
    condition     = length(var.TWILIO_ACCOUNT_SID) > 2 && substr(var.TWILIO_ACCOUNT_SID, 0, 2) == "AC"
    error_message = "TWILIO_ACCOUNT_SID expected to start with \"AC\"."
  }
}

variable "TWILIO_API_KEY" {
  type        = string
  sensitive   = true
  description = "Twilio API key"
  validation {
    condition     = length(var.TWILIO_API_KEY) > 2 && substr(var.TWILIO_API_KEY, 0, 2) == "SK"
    error_message = "TWILIO_API_KEY expected to start with \"SK\"."
  }
}

variable "TWILIO_API_SECRET" {
  type        = string
  sensitive   = true
  description = "Twilio API secret"
}

variable "SERVERLESS_DOMAIN" {
  type        = string
  description = "serverless domain"
  validation {
    condition     = length(var.SERVERLESS_DOMAIN) > 24 && substr(var.SERVERLESS_DOMAIN, 0, 24) == "serverless-agent-assist-"
    error_message = "SERVERLESS_DOMAIN expected to start with \"serverless-agent-assist-\"."
  }
}

variable "SERVERLESS_SID" {
  type        = string
  description = "serverless sid"
  validation {
    condition     = length(var.SERVERLESS_SID) > 2 && substr(var.SERVERLESS_SID, 0, 2) == "ZS"
    error_message = "SERVERLESS_SID expected to start with \"ZS\"."
  }
}

variable "SERVERLESS_ENV_SID" {
  type        = string
  description = "serverless env sid"
  validation {
    condition     = length(var.SERVERLESS_ENV_SID) > 2 && substr(var.SERVERLESS_ENV_SID, 0, 2) == "ZE"
    error_message = "SERVERLESS_ENV_SID expected to start with \"ZE\"."
  }
}

variable "TWILIO_FLEX_WORKSPACE_SID" {
  type        = string
  description = "TaskRouter workspace sid"
  validation {
    condition     = length(var.TWILIO_FLEX_WORKSPACE_SID) > 2 && substr(var.TWILIO_FLEX_WORKSPACE_SID, 0, 2) == "WS"
    error_message = "TWILIO_FLEX_WORKSPACE_SID expected to start with \"WS\"."
  }
}






