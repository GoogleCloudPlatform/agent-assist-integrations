# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


variable "gcp_project_id" {
  type = string
}

variable "ui_connector_docker_image" {
  type = string
}

variable "cloud_pubsub_interceptor_docker_image" {
  type = string
}

variable "service_region" {
  default = "us-central1"
}

variable "agent_assist_notifications_topic_id" {
  description = "The topic id for agent assist suggestions."
  default     = "aa-new-suggestion-topic"
}

variable "new_message_notifications_topic_id" {
  description = "The topic id for new conversation messages."
  default     = "aa-new-message-topic"
}

variable "conversation_lifecycle_notifications_topic_id" {
  description = "The topic id for conversation lifecycle events."
  default     = "aa-conversation-event-topic"
}

variable "new_recognition_result_notification_topic_id" {
  description = "The topic id for new recognition result events."
  default     = "aa-intermediate-transcript-topic"
}


variable "auth_option" {
  default = ""
}

## ---------------------------------------------------------------------------------------------------------------------
## OPTIONAL PARAMETERS
## These variables have defaults and may be overridden.
## ---------------------------------------------------------------------------------------------------------------------

# The name of your JWT secret.
variable "jwt_secret_name" {
  default = "aa-integration-jwt-secret"
}

# Configurations for Memorystore for Redis.
# Deprecated. Direct VPC egress is used instead. https://cloud.google.com/run/docs/configuring/vpc-direct-vpc
# variable "vpc_connector_name" {
#   default = "aa-integration-vpc"
# }

# variable "vpc_network" {
#   default = "default"
# }

variable "redis_ip_range" {
  default = "10.8.0.0/28"
}

variable "redis_instance_id" {
  default = "aa-integration-redis"
}

# Configurations for Cloud Run services.
variable "connector_service_account_name" {
  default = "ui-connector"
}

variable "interceptor_service_account_name" {
  default = "cloud-pubsub-interceptor"
}

variable "connector_service_name" {
  default = "ui-connector"
}

variable "interceptor_service_name" {
  default = "cloud-pubsub-interceptor"
}

# Configurations for Cloud Pub/Sub topics and subscriptions.
variable "cloud_run_pubsub_invoker_name" {
  default = "cloud-run-pubsub-invoker"
}

variable "agent_assist_notifications_subscription_id" {
  description = "The subscription id for agent assist suggestions."
  default     = "aa-new-suggestion-sub"
}

variable "new_message_notifications_subscription_id" {
  description = "The subscription id for new conversation messages."
  default     = "aa-new-message-sub"
}

variable "conversation_lifecycle_notifications_subscription_id" {
  description = "The subscription id for conversation lifecycle events."
  default     = "aa-conversation-event-sub"
}

variable "new_recognition_result_notification_subscription_id" {
  description = "The subscription id for new recognition result, intermediate  events."
  default     = "aa-intermediate-transcript-event-sub"
}


## ---------------------------------------------------------------------------------------------------------------------
## DO NOT CHANGE
## These variables are predefined for the service.
## ---------------------------------------------------------------------------------------------------------------------

variable "gcp_services" {
  description = "A list of GCP Services needed for this deployment."
  type        = list(string)
  default = [
    "dialogflow.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    # "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "redis.googleapis.com",
    "iam.googleapis.com"
  ]
}

variable "connector_service_account_roles" {
  description = "A list of necessary IAM roles for UI Connector service account."
  type        = list(string)
  default = [
    "roles/redis.editor",
    "roles/vpcaccess.user",
    "roles/compute.viewer",
    "roles/secretmanager.secretAccessor",
    "roles/dialogflow.agentAssistClient"
  ]
}

variable "interceptor_service_account_roles" {
  description = "A list of necessary IAM roles for Cloud Pub/Sub Interceptor service account."
  type        = list(string)
  default = [
    "roles/redis.editor",
    "roles/vpcaccess.user",
    "roles/compute.viewer",
  ]
}

