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


provider "google-beta" {
  project = var.gcp_project_id
  region  = var.service_region
}

# Enable GCP Services
resource "google_project_service" "gcp_services" {
  for_each = toset(var.gcp_services)
  project  = var.gcp_project_id
  service  = each.key
  # Do not disable serives when the Terraform resource is destroyed.
  disable_dependent_services = false
  disable_on_destroy = false
}

## ---------------------------------------------------------------------------------------------------------------------
## Create Service Accounts
## ---------------------------------------------------------------------------------------------------------------------

# Create service account for UI Connector service runtime.
resource "google_service_account" "connector_service_account" {
  project    = var.gcp_project_id
  account_id = var.connector_service_account_name
  create_ignore_already_exists = true
}

# Add necessary IAM roles for UI Connector service account.
resource "google_project_iam_binding" "connector_service_account" {
  project  = var.gcp_project_id
  for_each = toset(var.connector_service_account_roles)
  role     = each.key
  members  = ["serviceAccount:${google_service_account.connector_service_account.email}"]
}

# Create service account for Cloud Pub/Sub Interceptor service runtime.
resource "google_service_account" "interceptor_service_account" {
  project    = var.gcp_project_id
  account_id = var.interceptor_service_account_name
  create_ignore_already_exists = true
}

# Add necessary IAM roles for Cloud Pub/Sub Interceptor service account.
resource "google_project_iam_binding" "interceptor_service_account" {
  project  = var.gcp_project_id
  for_each = toset(var.interceptor_service_account_roles)
  role     = each.key
  members  = ["serviceAccount:${google_service_account.interceptor_service_account.email}"]
}

## ---------------------------------------------------------------------------------------------------------------------
## Create a JWT Secret Key
## ---------------------------------------------------------------------------------------------------------------------

resource "random_uuid" "jwt_secret_key" {
}

resource "google_secret_manager_secret" "default" {
  project   = var.gcp_project_id
  secret_id = var.jwt_secret_name
  replication {
    user_managed {
      replicas {
        location = var.service_region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "default" {
  secret      = google_secret_manager_secret.default.name
  secret_data = random_uuid.jwt_secret_key.result
}

## ---------------------------------------------------------------------------------------------------------------------
## Setup Memorystore for Redis
## ---------------------------------------------------------------------------------------------------------------------

# Create a Redis instance in the same region as your Cloud Run services.
resource "google_redis_instance" "aa_integration_redis_instance" {
  project        = var.gcp_project_id
  name           = var.redis_instance_id
  memory_size_gb = 5
  region         = var.service_region
}

# Create a Serverless VPC Access connector with a custom IP range.
# Deprecated. Direct VPC egress is used instead. https://cloud.google.com/run/docs/configuring/vpc-direct-vpc
# resource "google_vpc_access_connector" "aa_integration_vpc" {
#   project       = var.gcp_project_id
#   name          = var.vpc_connector_name
#   ip_cidr_range = var.redis_ip_range
#   network       = var.vpc_network
#   region        = var.service_region
# }

## ---------------------------------------------------------------------------------------------------------------------
## Deploy UI Connector Service
## ---------------------------------------------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "ui_connector" {
  project      = var.gcp_project_id
  name         = var.connector_service_name
  location     = var.service_region
  launch_stage = "BETA"
  client       = "terraform"

  template {
    volumes {
      name = "my-service-volume"
      secret {
        secret = google_secret_manager_secret.default.secret_id
        items {
          version = "latest"
          path    = "jwt_secret_key"
          mode    = 0 # use default 0444
        }
      }
    }
    containers {
      image = var.ui_connector_docker_image
      volume_mounts {
        name       = "my-service-volume"
        mount_path = "/secret"
      }
      env {
        name  = "REDISHOST"
        value = google_redis_instance.aa_integration_redis_instance.host
      }
      env {
        name  = "REDISPORT"
        value = google_redis_instance.aa_integration_redis_instance.port
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "AUTH_OPTION"
        value = var.auth_option
      }
    }
    service_account = google_service_account.connector_service_account.email
    timeout         = "3600s"
    scaling {
      min_instance_count = 1
      # Add to prevent violation: "max_instance_count: must be greater or equal than min_instance_count.""
      max_instance_count = 100
    }
    vpc_access {
      network_interfaces {
        network    = "default"
        subnetwork = "default"
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }
}

resource "google_cloud_run_service_iam_binding" "ui_connector_invoker_binding" {
  project  = var.gcp_project_id
  location = google_cloud_run_v2_service.ui_connector.location
  service  = google_cloud_run_v2_service.ui_connector.name
  role     = "roles/run.invoker"
  members = [
    "allUsers"
  ]
}

## ---------------------------------------------------------------------------------------------------------------------
## Deploy Cloud PubSub Interceptor Service
## ---------------------------------------------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "cloud_pubsub_interceptor" {
  project      = var.gcp_project_id
  name         = var.interceptor_service_name
  location     = var.service_region
  client       = "terraform"
  launch_stage = "BETA"
  ingress      = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    containers {
      image = var.cloud_pubsub_interceptor_docker_image
      env {
        name  = "REDISHOST"
        value = google_redis_instance.aa_integration_redis_instance.host
      }
      env {
        name  = "REDISPORT"
        value = google_redis_instance.aa_integration_redis_instance.port
      }
    }
    service_account = google_service_account.interceptor_service_account.email
    scaling {
      min_instance_count = 1
      # Add to prevent violation: "max_instance_count: must be greater or equal than min_instance_count.""
      max_instance_count = 100
    }
    vpc_access {
      network_interfaces {
        network    = "default"
        subnetwork = "default"
      }
      egress = "ALL_TRAFFIC"
    }
  }
}

## ---------------------------------------------------------------------------------------------------------------------
## Configure Cloud PubSub Topic Subscriptions
## ---------------------------------------------------------------------------------------------------------------------

# Create a service account to represent the Pub/Sub subscription identity.
resource "google_service_account" "pubsub_service_account" {
  project      = var.gcp_project_id
  account_id   = var.cloud_run_pubsub_invoker_name
  display_name = "Cloud Run Pub/Sub Invoker"
  create_ignore_already_exists = true
}

# Give the service account permission to invoke your interceptor service.
resource "google_cloud_run_service_iam_binding" "pubsub_invoker_binding" {
  project  = var.gcp_project_id
  location = google_cloud_run_v2_service.cloud_pubsub_interceptor.location
  service  = google_cloud_run_v2_service.cloud_pubsub_interceptor.name
  role     = "roles/run.invoker"
  members  = ["serviceAccount:${google_service_account.pubsub_service_account.email}"]
}

# Create a subscription for the Pub/Sub topic you configured for new suggestions.
resource "google_pubsub_topic" "suggestion_topic" {
  project = var.gcp_project_id
  name    = var.agent_assist_notifications_topic_id
}
resource "google_pubsub_subscription" "suggestion_subscription" {
  project = var.gcp_project_id
  name    = var.agent_assist_notifications_subscription_id
  topic   = google_pubsub_topic.suggestion_topic.name
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.cloud_pubsub_interceptor.uri}/human-agent-assistant-event"
    oidc_token {
      service_account_email = google_service_account.pubsub_service_account.email
    }
    attributes = {
      x-goog-version = "v1"
    }
  }
  expiration_policy {
    ttl = ""
  }
  depends_on = [google_cloud_run_v2_service.cloud_pubsub_interceptor]
}

# Create a subscription for the Pub/Sub topic you configured for new message events.
resource "google_pubsub_topic" "new_message_topic" {
  project = var.gcp_project_id
  name    = var.new_message_notifications_topic_id
}
resource "google_pubsub_subscription" "new_message_subscription" {
  project = var.gcp_project_id
  name    = var.new_message_notifications_subscription_id
  topic   = google_pubsub_topic.new_message_topic.name
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.cloud_pubsub_interceptor.uri}/new-message-event"
    oidc_token {
      service_account_email = google_service_account.pubsub_service_account.email
    }
    attributes = {
      x-goog-version = "v1"
    }
  }
  expiration_policy {
    ttl = ""
  }
  depends_on = [google_cloud_run_v2_service.cloud_pubsub_interceptor]
}

# Create a subscription for the Pub/Sub topic you configured for conversation lifecycle events.
resource "google_pubsub_topic" "conversation_lifecycle_topic" {
  project = var.gcp_project_id
  name    = var.conversation_lifecycle_notifications_topic_id
}
resource "google_pubsub_subscription" "conversation_lifecycle_subscription" {
  project = var.gcp_project_id
  name    = var.conversation_lifecycle_notifications_subscription_id
  topic   = google_pubsub_topic.conversation_lifecycle_topic.name
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.cloud_pubsub_interceptor.uri}/conversation-lifecycle-event"
    oidc_token {
      service_account_email = google_service_account.pubsub_service_account.email
    }
    attributes = {
      x-goog-version = "v1"
    }
  }
  expiration_policy {
    ttl = ""
  }
  depends_on = [google_cloud_run_v2_service.cloud_pubsub_interceptor]
}



# Create a subscription for the Pub/Sub topic you configured for new recognition result notification events.
resource "google_pubsub_topic" "new_recognition_result_notification_topic" {
  project = var.gcp_project_id
  name    = var.new_recognition_result_notification_topic_id
}
resource "google_pubsub_subscription" "new_recognition_result_notification_subscription" {
  project = var.gcp_project_id
  name    = var.new_recognition_result_notification_subscription_id
  topic   = google_pubsub_topic.new_recognition_result_notification_topic.name
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.cloud_pubsub_interceptor.uri}/new-recognition-result-notification-event"
    oidc_token {
      service_account_email = google_service_account.pubsub_service_account.email
    }
    attributes = {
      x-goog-version = "v1"
    }
  }
  expiration_policy {
    ttl = ""
  }
  depends_on = [google_cloud_run_v2_service.cloud_pubsub_interceptor]
}
