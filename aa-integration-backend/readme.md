# Agent Assist Integration Services

A backend infrastructure for Agent Assist integration, including Cloud Pub/Sub Interceptor service and UI Connector service. The Interceptor processes feature-related event notifications from Dialogflow via [Cloud Pub/Sub](https://cloud.google.com/pubsub/docs/publisher) topics and then UI Connector pushes them to Agent Desktop UI. UI Connector also supports feedback signals from Agent Desktop and sends them to Dialogflow.

**Content**

1. [Directory](#directory)
2. [Structure](#structure)
    - [Cloud Pub/Sub](#cloud-pubsub)
    - [Cloud Pub/Sub Interceptor (deployed on Cloud Run)](#cloud-pubsub-interceptor-deployed-on-cloud-run)
    - [Redis (using Memorystore for Redis)](#redis-using-memorystore-for-redis)
    - [UI Connector (deployed on Cloud Run)](#ui-connector-deployed-on-cloud-run)
    - [Secret Manager](#secret-manager)
3. [Workflows](#workflows)
    - [Workflow 0: JWT registration (UI Connector)](#workflow-0-jwt-registration-ui-connector)
    - [Workflow 1: AA event handling](#workflow-1-aa-event-handling)
    - [Workflow 2: Dialogflow request processing](#workflow-2-dialogflow-request-processing)
4. [APIs](#apis)
    - [Cloud Pub/Sub Interceptor](#cloud-pubsub-interceptor)
    - [UI Connector](#ui-connector)
      - [JWT Registration API](#jwt-registration-api)
      - [Dialogflow Proxy APIs](#dialogflow-proxy-apis)
5. [Automated Deployment](#automated-deployment)
6. [Connection Test](#connection-test)
7. [How to Deploy and Run Manually](#how-to-deploy-and-run-manually)
    - [Prerequisite](#prerequisite)
    - [Set up Environment Variables](#set-up-environment-variables)
    - [Authorize GCP Processes](#authorize-gcp-processes)
    - [Customize User Authentication Method](#customize-user-authentication-method)
    - [Customize Allowed Origins (Recommended)](#customize-allowed-origins-recommended)
    - [Generate and Store JWT Secret Key](#generate-and-store-jwt-secret-key)
    - [Memorystore for Redis Setup](#memorystore-for-redis-setup)
    - [Deploy UI Connector Service](#deploy-ui-connector-service)
    - [Deploy Cloud Pub/Sub Interceptor Service](#deploy-cloud-pubsub-interceptor-service)
    - [Configure Cloud Pub/Sub Subscriptions](#configure-cloud-pubsub-subscriptions)
8. [(Optional) Integration with Cloud Build](#optional-integration-with-cloud-build)

# Directory

```
.
├── LICENSE
├── cloud-pubsub-interceptor
│   ├── Dockerfile - Builds Docker image for Cloud Pub/Sub Interceptor deployment on Cloud Run
│   ├── main.py - A starter for flask app
│   ├── requirements.txt
│   └── unit_test.py - Unit test code for Cloud Pub/Sub Interceptor
├── cloudbuild.yaml - An example configuration file for Cloud Build
├── deploy.sh - An automated deployment script
├── images
├── readme.md
└── ui-connector
    ├── Dockerfile - Builds Docker image for UI Connector deployment on Cloud Run
    ├── auth.py - Handles JWT validation and registration
    ├── auth_options.py - Supports authentication via different identity providers
    ├── config.py - Configures variables about authentication, logging and CORS origins
    ├── dialogflow.py - Includes dialogflow utilities for handling conversations at runtime
    ├── main.py - A starter for flask app
    ├── requirements.txt
    ├── templates
    │   └── index.html - A simple interactive demo
    └── unit_test.py - Unit test code for UI Connector
```

# Structure

![](images/structure.jpg)

## [Cloud Pub/Sub](https://cloud.google.com/pubsub/docs/publisher)

Cloud Pub/Sub topics should be configured in conversation profiles. Agent Assist will publish suggestions, new messages and conversation lifecycle related events to the topic, with  suggestions in the form of [HumanAgentAssistantEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/HumanAgentAssistantEvent) and both new messages and conversation lifecycle events and new recognition result notification events are packed as [ConversationEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/ConversationEvent). For each conversation profile, these four kinds of event messages are published to different topics. A sample conversation lifecycle event message can be `{"conversation":"projects/your-project-id/locations/global/conversations/your-conversation-id","type":"CONVERSATION_STARTED"}`, which indicates the start of a conversation.

## Cloud Pub/Sub Interceptor (deployed on [Cloud Run](https://cloud.google.com/run/docs))

The functionality of each container instance (server) of this Cloud Run service is identical to each other, including:

1. Processing event messages posted by Cloud Pub/Sub topics via HTTP requests.
2. Publishing those received to Redis Pub/Sub channels specific to the conversation name and id of the UI connector server that handles the conversation. The channel format is `{connector_id}:{conversation_name}`.

## Redis (using [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis/redis-overview))

1. Records the UI Connector server id information for each conversation in mapping `<conversation_name, connector_id>`
2. Forwards event notifications published by Cloud Pub/Sub Interceptor to the corresponding UI Connector server via Redis Pub/Sub mechanism.

## UI Connector (deployed on [Cloud Run](https://cloud.google.com/run/docs))

As WebSockets connections are stateful, the agent desktop will stay connected to the same container on Cloud Run throughout the lifespan of the connection. So every UI Connector server handles different conversations and subscribes to distinct Redis Pub/Sub channels `{connector_id}:*` for those conversations they handle. Tasks for each UI Connector server are listed below.

1. Supports a customized authentication method for agent desktops.
2. Generates temporary JWT after authenticating agent desktops’ customized tokens. When they send requests for Dialogflow API or WebSockets connection, UI Connector validates the attached JWT instead of checking the original agent token.
3. Establishes a WebSockets connection with the authenticated agent desktop based on a given conversation name.
4. Subscribes event messages to Redis Pub/Sub channels for conversations it handles.
5. Pushes Agent Assist events to the desktop UI as they are received.

## [Secret Manager](https://cloud.google.com/secret-manager)

UI Connector needs a JWT secret key for generating temporary JWTs for authenticated agent desktops. This secret key will be stored in the Secret Manager.

# Workflows

With the five components above, the backend infrastructure works for two typical workflows: AA event handling and Dialogflow request processing. Both of them should be protected by a valid JWT, which can be registered via a HTTP request with a customized token.

## Workflow 0: JWT registration (UI Connector)

Before any workflow, agent desktop should send a HTTP request to UI Connector for JWT registration. The customers should customize the authorization requirement before it accepts any Authorization header of the registration request. For example, if a business customer wants to use Salesforce Bearer tokens to authenticate an agent desktop, they can enforce UI Connector to call the Salesforce backend to check Authorization header passed by the agent desktop.

### Steps

1. Agent UI posts a HTTP request with customized token to UI Connector. An optional user name can also be passed as a JSON request body.
2. UI Connector returns a temporary JWT (lifetime: 1h) for the client if the customized token is valid, or returns an error message if invalid.
   ![](images/workflow0_jwt.png)

## Workflow 1: AA event handling

For handling Agent Assist event notifications, Cloud Pub/Sub Interceptor keeps processing messages posted by Cloud Pub/Sub topics and publishing to Redis Pub/Sub channels `{connector_id}:{conversation_name}`, while UI Connector servers send those events to agent desktop via WebSockets connection as they are received.

### Steps

For each conversation, the workflow for receiving Dialogflow events include these steps.

1. Agent UI initiates WebSockets connection with a temporary JWT.
2. UI Connector receives the connection request after verifying JWT, or connection error is reported.
3. Agent UI registers the conversation by sending a conversation name to UI Connector.
4. As Dialogflow publishes new event notifications to Cloud Pub/Sub topics, Cloud Pub/Sub Interceptor republishes those messages posted by Cloud Pub/Sub topics to Redis Pub/Sub channels `{connector_id}:{conversation_name}`.
5. UI Connector sends Dialogflow events to the client via WebSockets connection whenever it receives new messages from Redis Pub/Sub channels `{connector_id}:*`.
   ![](images/workflow1_event.png)

## Workflow 2: Dialogflow request processing

Besides building WebSockets connection, UI Connector also works as a Dialogflow proxy for forwarding feedback signals from agent desktop to Dialogflow. Currently it supports these Dialogflow HTTP requests:

`GET:  /location/*/conversations/**, /location/*/conversationProfiles/**, /location/*/conversationModels/**`

`POST: /location/*/conversations, /location/*/conversations/**`

`PATCH: /location/*/answerRecords/**, /location/*/conversations/**`

### Steps

After getting valid JWT, the steps for sending Dialogflow calls are listed below.

1. Agent UI sends HTTP requests along with a JWT as its `Authorization` header.
2. UI Connector validates the JWT and checks whether the request path could be converted to available Dialogflow HTTP request. If yes, it sends DialogflowRequest and forwards original DialogflowResponse to Agent UI.
   ![](images/workflow2_proxy.png)

# APIs

## Cloud Pub/Sub Interceptor

The interceptor is dedicated to receiving messages posted by Cloud Pub/Sub topics. It expects suggestions for human agents, new messages, new recognition result notifications and conversation lifecycle events posted to four separate request URLs.

`POST /human-agent-assistant-event`

**Request Body**
The request body should be JSON data that contains a [HumanAgentAssistantEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/HumanAgentAssistantEvent) as [PubSubMessage](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).data.

**Response**
It returns a `204` status code with additional information, which is considered as a message acknowledgement by Cloud Pub/Sub.

**Exception**
A bad request returns a `400` status code and corresponding error message.

`POST /conversation-lifecycle-event`

**Request Body**
The request body should be JSON data that contains a [ConversationEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/ConversationEvent) as [PubSubMessage](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).data.

**Response**
It returns a `204` status code with additional information, which is considered as a message acknowledgement by Cloud Pub/Sub.

**Exception**
A bad request returns a `400` status code and corresponding error message.

`POST /new-message-event`

**Request Body**
The request body should be JSON data that contains a [ConversationEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/ConversationEvent) as [PubSubMessage](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).data.

**Response**
It returns a `204` status code with additional information, which is considered as a message acknowledgement by Cloud Pub/Sub.


`POST /new-recognition-result-notification-event`

**Request Body**
The request body should be JSON data that contains a [ConversationEvent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/ConversationEvent) [PubSubMessage](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).data And the request body should also contains [PubSubMessage attribues](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage) 'participant_role' and 'message_id'.

**Response**
It returns a `204` status code with additional information, which is considered as a message acknowledgement by Cloud Pub/Sub.

**Exception**
A bad request returns a `400` status code and corresponding error message.

## UI Connector

UI Connector serves external requests via three API modules, including SocketIO APIs, Dialogflow Proxy APIs and JWT Registration API.

1. JWT Registration API: It expects HTTP requests with valid customized tokens and returns a newly-generated JWT with 1h lifetime to the client. The API wouldn't work until the customized rule to authenticate agent clients is implemented. The encoding algorithm must be the same as the one used in the decoding, and currently ‘HS256’ is used.
2. SocketIO APIs: They handle WebSockets connections between clients and servers, including establishing connections and sending Dialogflow events to associated clients.
3. Dialogflow Proxy APIs: It receives clients’ requests for sending feedback signals to Dialogflow. Every request should have a valid JWT as its header, or connector servers would reject it.

### JWT Registration API

`POST /register`

**Request Header**
Authorization: {CustomizedToken}

**Request Body**
The request body can be empty, or contains JSON data {"gcp_agent_assist_user": UserName}.

**Response**
If successful, the response body contains generated JWT in JSON format.

Example:
{
"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2Mzg4MzU3ODZ9.khHlrdxNTnnaON5m-5r_0-e7Si3THGp2gSC3k0oQMGQ"
}

**Exception**
A bad request returns `401` status code and corresponding error message.

### SocketIO APIs

This API group handles WebSockets connections between clients and servers, including establishing connections and sending Dialogflow events to associated clients. The connection request should be authorized with a valid JWT.
Every WebSockets API is a socketio event. The following shows event names and expected messages in the format `EVENT_NAME(EXPECTED_MESSAGE)`.

```python
# Events emitted by clients
connect({'token': generated_JWT}) # Receives connection requests from clients and expects clients to provide valid JWT for authorization. It emits an 'unauthenticated' event if no valid token is received.
disconnect() # Receives disconnection event from clients and clear mapping data <conversation_name, server_id> from redis.
join-conversation(conversation_name) # Registers conversation on server with its conversation name.

# Events emitted by servers
unauthenticated() # Indicates that connection requests from clients are not authenticated with valid token
human-agent-assistant-event({
    'conversation_name': conversation_name,
    'data': data,
    'data_type': 'human-agent-assistant-event',
    'publish_time': pubsub_message['publishTime'],
    'message_id': pubsub_message['messageId']
}) # Sends HumanAgentAssistantEvent notification pushed by Cloud Pub/Sub
conversation-lifecycle-event({
  'conversation_name': conversation_name,
  'data': data,
  'data_type': 'conversation-lifecycle-event',
  'publish_time': pubsub_message['publishTime'],
  'message_id': pubsub_message['messageId']
}) # Sends conversation lifecycle event notification pushed by Cloud Pub/Sub
new-message-event({
  'conversation_name': conversation_name,
  'data': data,
  'data_type': 'new-message-event',
  'publish_time': pubsub_message['publishTime'],
  'message_id': pubsub_message['messageId']
}) # Sends new message event notification pushed by Cloud Pub/Sub
new-recognition-result-notification-event({
  'conversation_name': conversation_name,
  'data': data,
  'data_type': 'new-recognition-result-notification-event',
  'publish_time': pubsub_message['publishTime'],
  'message_id': pubsub_message['messageId']
  'participant_role': pubsub_message['attributes']['participant_role']
  'new_recognition_result_message_id': pubsub_message['attributes']['message_id']
}) # Sends new recognition result notification pushed by Cloud Pub/Sub
```

### Dialogflow Proxy APIs

These APIs handle client requests about sending feedback signals to Dialogflow.

| Dialogflow Proxy API      | Dialogflow API |
| -------------- | -------------- |
| `PATCH /<version>/projects/<project>/locations/<location>/answerRecords/<path>`| [projects.locations.answerRecords.patch](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.answerRecords/patch)|
| `GET /<version>/projects/<project>/locations/<location>/conversations/<path>`| [projects.locations.conversations.get](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.conversations/get), [projects.locations.conversations.messages.list](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.conversations.messages/list), [projects.locations.conversations.participants.get](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants/get), [projects.locations.conversations.participants.list](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants/list) |
| `POST /<version>/projects/<project>/locations/<location>/conversations/<path>`| [projects.locations.conversations.complete](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations/complete), [projects.locations.conversations.create](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations/create), [projects.locations.conversations.messages.batchCreate](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.messages/batchCreate), [projects.locations.conversations.participants.analyzeContent](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants/analyzeContent), [projects.locations.conversations.participants.create](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants/create), [projects.locations.conversations.participants.suggestions.suggestArticles](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants.suggestions/suggestArticles), [projects.locations.conversations.participants.suggestions.suggestFaqAnswers](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants.suggestions/suggestFaqAnswers), [projects.locations.conversations.participants.suggestions.suggestSmartReplies](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants.suggestions/suggestSmartReplies)|
| `PATCH /<version>/projects/<project>/locations/<location>/conversations/<path>`| [projects.locations.conversations.participants.patch](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations.participants/patch)|
| `POST /<version>/projects/<project>/locations/<location>/conversations`| [projects.locations.conversations.create](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversations/create)|
| `GET /<version>/projects/<project>/locations/<location>/conversationProfiles/<path>`| [projects.locations.conversationProfiles.get](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1/projects.locations.conversationProfiles/get)|
| `GET /<version>/projects/<project>/locations/<location>/conversationModels/<path>`| [projects.locations.conversationModels.get](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.locations.conversationModels/get)|
|  |  |

`PATCH /<version>/projects/<project>/locations/<location>/answerRecords/<path>`

`GET/POST/PATCH /<version>/projects/<project>/locations/<location>/conversations/<path>`

`POST /<version>/projects/<project>/locations/<location>/conversations`

`GET /<version>/projects/<project>/locations/<location>/conversationProfiles/<path>`

`GET /<version>/projects/<project>/locations/<location>/conversationModels/<path>`

`GET /<version>/projects/<project>/locations/<location>/suggestions:searchKnowledge`

`GET /<version>/projects/<project>/locations/<location>/statelessSuggestion:generate`

`GET /<version>/projects/<project>/locations/<location>/generators/<path:path>`

**Request Headers**
Authorization: {ValidJWT}

**Request Body**
For the `GET` method, the request body can be empty. For `POST` and `PATCH` methods, the request body should contain JSON data expected to be sent to Dialogflow.

**Response**
If a valid JWT is attached in the request, the original response from Dialogflow will be processed and returned, including raw content, status code and headers, or status code `401` and error message ‘Token is missing.’ or ‘Token is invalid’ are returned.

# Automated Deployment
The deployment can be automated by a gcloud automation script or terraform.

## Automation Script
Check `./deploy.sh` for more details.

## Terraform
All terraform files are included under folder `/terraform`. Before applying terraform changes, please clone this repository and complete the following steps.
1. Make sure your account has Owner permissions in your GCP project or been granted the following IAM roles.
    - Project IAM Admin (roles/resourcemanager.projectIamAdmin)
    - Service Usage Admin (roles/serviceusage.serviceUsageAdmin)
    - Service Account Admin (roles/iam.serviceAccountAdmin)
    - Service Account User (roles/iam.serviceAccountUser)
    - Pub/Sub Admin (roles/pubsub.admin)
    - Secret Manager Admin (roles/secretmanager.admin)
    - Cloud Build Editor (roles/cloudbuild.builds.editor)
    - Artifact Registry Administrator (roles/artifactregistry.admin)
    - Storage Admin (roles/storage.admin)
    - Cloud Run Admin (roles/run.admin)
    - Cloud Memorystore Redis Admin (roles/redis.admin)
    - Serverless VPC Access Admin (roles/vpcaccess.admin)
2. Build images for UI Connector and Cloud Pub/Sub Interceptor and note the image names.
```bash
# Example
# Under './ui-connector' folder.
$ gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/aa-integration-backend/ui-connector
# Under './cloud-pubsub-interceptor' folder.
$ gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/aa-integration-backend/cloud-pubsub-interceptor
```
3. Create a GCS bucket to store terraform state and update the backend bucket value at `/terraform/backend.tf`.
```bash
GCP_PROJECT_ID=$(gcloud config get-value project)
# Create the Cloud Storage bucket.
gsutil mb gs://${GCP_PROJECT_ID}-tfstate
# Enable Object Versioning to keep the history of your deployments.
gsutil versioning set on gs://${GCP_PROJECT_ID}-tfstate
```
4. Export the value of required terraform variables `gcp_project_id`, `ui_connector_docker_image` and `cloud_pubsub_interceptor_docker_image`. Example: `export TF_VAR_gcp_project_id='you-gcp-project-id'`. (Alternatively, you can fill their values at `/terraform/variables.tf` directly.)
5. Customize authentication method by modifying `auth.check_auth()` method at `/ui-connector/auth.py`.

If you want to automate these steps by using Cloud Build, follow this [instruction](https://cloud.google.com/build/docs/automate-builds) and use the build configuration file `./terraform_cloudbuild.yaml`. To allow Cloud Build to deploy the services, you need to grant Cloud Build Service Account the IAM roles listed at Step 1.

# How to Deploy and Run

An automation script has been provided at `./deploy.sh`. If you want to deploy it step by step, please check the following process.

## Prerequisite

1. [Install Google Cloud CLI ](https://cloud.google.com/sdk/docs/install-sdk) if you haven't configured it.
2. [Create a Cloud Pub/Sub topic](https://cloud.google.com/pubsub/docs/admin#create_a_topic) for each kind of event notification you need from Dialogflow. Please note the topic id and topic name for later backend deployment.
3. [Configure your conversation profile](https://cloud.google.com/agent-assist/docs/conversation-profile) using [Agent Assist console](https://agentassist.cloud.google.com/) with Cloud Pub/Sub topics topics.

## Set up Environment Variables

To make the commands for deployment simpler, we recommend you to set useful environment variables.

```bash
$ export GCP_PROJECT_ID='aa-integration-service'
```

Please prepare the following environment variables as you deploy the infrastructure as instructed.

1. `GCP_PROJECT_ID`: the project id of your GCP project that hosts related resources.
2. `INTERCEPTOR_SERVICE_NAME`: the Cloud Run service name of your Cloud Pub/Sub Interceptor.
3. `INTERCEPTOR_IMAGE_NAME`: the image name of your Cloud Pub/Sub Interceptor service.
4. `INTERCEPTOR_SERVICE_ACCOUNT_NAME`: the service account for Cloud Pub/Sub Interceptor runtime.
5. `CONNECTOR_SERVICE_NAME`: the Cloud Run service name of your UI Connector.
6. `CONNECTOR_IMAGE_NAME`: the image name of your UI Connector service.
7. `CONNECTOR_SERVICE_ACCOUNT_NAME`: the service account for UI Connector runtime.
8. `JWT_SECRET_NAME`: the name of your JWT secret key stored in [Secret Manager](https://cloud.google.com/secret-manager/docs).
9. `SERVICE_REGION`: the location or region of your services and related GCP resources.
10. `VPC_CONNECTOR_NAME`: (optional) the name of your [Serverless VPC Access connector](https://cloud.google.com/run/docs/configuring/connecting-vpc#create-connector) for connecting Cloud Run services to [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis/redis-overview).
11. `VPC_NETWORK`: the name of the authorized VPC network that your Redis instance is attached to. The value should be 'default' if you do not set up VPC for your GCP project.
12. `VPC_SUBNET`: the name of the authorized VPC network that your Redis instance is attached to. The value should be 'default' if you haven't customized VPC network settings.
13. `REDIS_IP_RANGE`: (optional) an unreserved internal IP network for your Serverless VPC Access connector. A '/28' of unallocated space is required, for example, 10.8.0.0/28 works in most new projects.
14. `AUTH_OPTION`: The option of authenticating users when registering JWT. By default it's empty and no users are allowed to register JWT via UI Connector service. Supported values: 'SalesforceLWC', 'Salesforce', 'GenesysCloud', 'Twilio', 'Skip' (skip auth token verification, should not be used in production).

## Authorize GCP Processes
Using separate GCP accounts for service administration and runtime identity in your GCP project is recommended, as service administration is mainly performed by humans with [Google accounts](https://cloud.google.com/iam/docs/overview#google_account) and the latter one is to grant Cloud Run services permissions via [service accounts](https://cloud.google.com/iam/docs/overview#service_account) to enable their access to necessary resources.

The roles granted to your administrator's Google account and the service accounts created for Cloud Run services apply to at most the whole GCP project.

### Prepare Google Account for Service Administration

To manage this backend infrastructure, the administrator account should be granted the following IAM Roles. Their permissions are all included in the [basic roles](https://cloud.google.com/iam/docs/understanding-roles#basic) Editor (roles/editor) and Owner (roles/owner). However, we recommend that you grant predefined roles where possible to compy with the [security principle of least privilege](https://cloud.google.com/iam/docs/using-iam-securely#least_privilege).

1. [Secret Manager Admin (roles/secretmanager.admin)](https://cloud.google.com/secret-manager/docs/access-control): manage secrets stored in Secret Manager for JWT generation and verification.
2. [Cloud Run Admin (roles/run.admin)](https://cloud.google.com/run/docs/reference/iam/roles): deploy and manage Cloud Run services.
3. [Service Account User (roles/iam.serviceAccountUser)](https://cloud.google.com/iam/docs/service-accounts#user-role): grant Cloud Run runtime service accounts [iam.serviceAccounts.actAs](iam.serviceAccounts.actAs) permissions.
4. [Cloud Build Editor (roles/cloudbuild.builds.editor)](https://cloud.google.com/build/docs/iam-roles-permissions): build Docker images for the integration services using Cloud Build.
5. [Artifact Registry Administrator](roles/artifactregistry.admin): store and manage built Docker images for the integration services.
6. [Cloud Pub/Sub Editor (roles/pubsub.editor)](https://cloud.google.com/pubsub/docs/access-control#roles): create and manage Cloud Pub/Sub topics and subscriptions.
7. [Redis Admin (roles/redis.admin)](https://cloud.google.com/memorystore/docs/redis/access-control#predefined_roles): create and manage Memorystore for Redis resources.

To deploy this backend infrastructure using gcloud CLI, you should set your Google account as the active account.

```bash
$ gcloud config set account $ADMIN_ACCOUNT
```

### Create Two Service Accounts for Cloud Run Runtime

We recommend giving every Cloud Run service a dedicated identity by assigning it a user-managed service account instead of using the default service account.

Check more details about [Service Identity](https://cloud.google.com/run/docs/securing/service-identity#gcloud) and [creating a service account](https://cloud.google.com/iam/docs/creating-managing-service-accounts#creating).

Required IAM roles for Cloud Pub/Sub Interceptor service account:

1. [Redis Editor(roles/redis.editor)](https://cloud.google.com/memorystore/docs/redis/access-control): update data in Memorystore for Redis instance.
2. [Serverless VPC Access User(roles/vpcaccess.user)](https://cloud.google.com/iam/docs/understanding-roles) and [Compute Viewer(roles/compute.viewer)](https://cloud.google.com/iam/docs/understanding-roles#compute-engine-roles): use Serverless VPC Access connectors to connect with Redis instance.

Required IAM roles for UI Connector service account:

1. [Redis Editor(roles/redis.editor)](https://cloud.google.com/memorystore/docs/redis/access-control): update data in Memorystore for Redis instance.
2. [Serverless VPC Access User(roles/vpcaccess.user)](https://cloud.google.com/iam/docs/understanding-roles) and [Compute Viewer(roles/compute.viewer)](https://cloud.google.com/iam/docs/understanding-roles#compute-engine-roles): use Serverless VPC Access connectors to connect with Redis instance.
3. [Secret Manager Secret Accessor(roles/secretmanager.secretAccessor)](https://cloud.google.com/iam/docs/understanding-roles#secret-manager-roles): read the payload of JWT secret key stored in Secret Manager.
4. [Dialogflow Agent Assist Client(roles/dialogflow.agentAssistClient)](https://cloud.google.com/iam/docs/understanding-roles#dialogflow-roles): access Dialogflow APIs for agents to handle live conversations using Agent Assist features.

## Customize User Authentication Method

Implement your authentication method `auth.check_auth` or specify supported identity provider via setting the environment variable `AUTH_OPTION` at `ui-connector/config.py`. If without any changes, it returns false for any token attached to JWT generation requests.

```bash
# By default it's empty and no users are allowed to register JWT via UI Connector service.
# Supported values:
#   1. 'SalesforceLWC': verify a SF OAuth Client Credentials auth token using the `oauth2/userinfo` REST endpoint. Required environment variables: SALESFORCE_ORGANIZATION_ID, SALESFORCE_DOMAIN.
#   2. 'Salesforce': verify the auth token using Salesforce OpenID Connect. Required environment variable: SALESFORCE_ORGANIZATION_ID.
#   3. 'GenesysCloud': verify the auth token using Genesys SDK UsersAPI.
#   4. 'Twilio': verify the auth token for Twilio. Required environment variable: TWILIO_FLEX_ENVIRONMENT.
#   5. 'Skip': skip auth token verification, should not be used in production.
$ export AUTH_OPTION='Salesforce'
```

## Customize Allowed Origins (Recommended)

To limit the origins that can access your service, please change the value of `config.CORS_ALLOWED_ORIGINS` variable. The default value `*` will allow any origin to visit your service.

## Generate and Store JWT Secret Key

1. Generate your JWT secret key. You could use python [secrets](https://docs.python.org/3/library/secrets.html) to generate secure random numbers for it.

```python
# generate_secret_key.py
import secrets
jwt_secret_key = secrets.token_bytes(16)
print(jwt_secret_key) # Output example: b'L\x9b\xd6i4\xc3\x1d\x95\xe3\xf78z\xdda\x97\xec'
```

2. Store the secret key in Secret Manager.

```bash
$ python generate_secret_key.py | gcloud secrets create $JWT_SECRET_NAME --data-file=- \
--replication-policy=user-managed --locations=$SERVICE_REGION
```

## Memorystore for Redis Setup

1. Create a Redis instance in the same region as your Cloud Run services.

```bash
$ gcloud redis instances create $REDIS_INSTANCE_ID --size=5 --region=$SERVICE_REGION
```

2. (Optional) You can connect to a Redis instance from Cloud Run by using [Direct Egress or Serverless VPC Access](https://cloud.google.com/memorystore/docs/redis/connect-redis-instance-cloud-run). If you choose Serverless VPC Access, you'll need to create a Serverless VPC Access connector. See this [guide](https://cloud.google.com/run/docs/configuring/connecting-vpc#create-connector) if more instructions are needed.

```bash
# Ensure the Serverless VPC Access API is enabled for your project.
$ gcloud services enable vpcaccess.googleapis.com
# Create a Serverless VPC Access connector with a custom IP range.
$ gcloud compute networks vpc-access connectors create $VPC_CONNECTOR_NAME \
--network $VPC_NETWORK \
--region $SERVICE_REGION \
--range $REDIS_IP_RANGE
```

Please note the IP Address and port number of your Redis instance as environment variables `REDIS_HOST` and `REDIS_PORT`.

## Deploy UI Connector Service

Under `/ui-connector` folder:

1. Build Docker image

```bash
$ gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/$CONNECTOR_IMAGE_NAME
```

2. Deploy to Cloud Run with Memorystore for Redis instance.

```bash
# Option 1: Use Direct Egress to connect for Redis connection.
$ gcloud run deploy $CONNECTOR_IMAGE_NAME \
--image gcr.io/$GCP_PROJECT_ID/$CONNECTOR_IMAGE_NAME \
--platform managed \
--service-account=$CONNECTOR_SERVICE_ACCOUNT_NAME \
--allow-unauthenticated \
--timeout 3600 \
--region $SERVICE_REGION \
--network $VPC_NETWORK \
--subnet $VPC_SUBNET \
--clear-vpc-connector \
--min-instances=1 \
--set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT,GCP_PROJECT_ID=$GCP_PROJECT_ID,AUTH_OPTION=$AUTH_OPTION \
--update-secrets=/secret/jwt_secret_key=${JWT_SECRET_NAME}:latest
# Option 2: Use a created Serverless VPC Access connector for Redis connection.
$ gcloud run deploy $CONNECTOR_IMAGE_NAME \
--image gcr.io/$GCP_PROJECT_ID/$CONNECTOR_IMAGE_NAME \
--platform managed \
--service-account=$CONNECTOR_SERVICE_ACCOUNT_NAME \
--allow-unauthenticated \
--timeout 3600 \
--region $SERVICE_REGION \
--vpc-connector $VPC_CONNECTOR_NAME \
--clear-network \
--min-instances=1 \
--set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT,GCP_PROJECT_ID=$GCP_PROJECT_ID,AUTH_OPTION=$AUTH_OPTION \
--update-secrets=/secret/jwt_secret_key=${JWT_SECRET_NAME}:latest
```

Note the service URL for deployed UI Connector, which will be used by clients (agent desktops).

## Deploy Cloud Pub/Sub Interceptor Service

Under `/cloud-pubsub-interceptor` folder:

1. Build Docker image

```bash
$ gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/$INTERCEPTOR_IMAGE_NAME
```

2. Deploy to Cloud Run with Redis

```bash
# Option 1: Use Direct Egress to connect for Redis connection.
$ gcloud run deploy $INTERCEPTOR_SERVICE_NAME \
--image gcr.io/$GCP_PROJECT_ID/$INTERCEPTOR_IMAGE_NAME \
--platform managed \
--service-account=$INTERCEPTOR_SERVICE_ACCOUNT_NAME \
--region $SERVICE_REGION \
--network $VPC_NETWORK \
--subnet $VPC_SUBNET \
--clear-vpc-connector \
--ingress=internal \
--min-instances=1 \
# You can also add LOGGING_FILE here to specify the logging file path on Cloud Run.
--set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT
# Option 2: Use a created Serverless VPC Access connector for Redis connection.
$ gcloud run deploy $INTERCEPTOR_SERVICE_NAME \
--image gcr.io/$GCP_PROJECT_ID/$INTERCEPTOR_IMAGE_NAME \
--platform managed \
--service-account=$INTERCEPTOR_SERVICE_ACCOUNT_NAME \
--region $SERVICE_REGION \
--vpc-connector $VPC_CONNECTOR_NAME \
--clear-network \
--ingress=internal \
--min-instances=1 \
# You can also add LOGGING_FILE here to specify the logging file path on Cloud Run.
--set-env-vars REDISHOST=$REDIS_HOST,REDISPORT=$REDIS_PORT
```

Note the service URL for deployed Cloud Pub/Sub Interceptor as environment variable `INTERCEPTOR_SERVICE_URL`.

## Configure Cloud Pub/Sub Subscriptions

Please create and configure your conversation profile with Cloud Pub/Sub topics before create subscriptions.

Here is an example of creating a conversation profile with Article Suggestion feature and four specified Cloud Pub/Sub topics. You could also check this [guide](https://cloud.google.com/agent-assist/docs/conversation-profile) for instructions about how to configure it on [Agent Assist Console](https://agentassist.cloud.google.com/).

HTTP method and URL:

```bash
POST https://dialogflow.googleapis.com/v2/projects/my-project-id/conversationProfiles
```

Request JSON body:

```bash
{
  "displayName": "my-conversation-profile-display-name",
  "humanAgentAssistantConfig": {
    "notificationConfig": {
      "topic": "projects/my-project-id/topics/aa-new-suggestion",
      "messageFormat": "JSON"
    },
    "humanAgentSuggestionConfig": {
      "featureConfigs": [
        {
          "enableEventBasedSuggestion": true,
          "suggestionFeature": {
            "type": "ARTICLE_SUGGESTION"
          },
          "queryConfig": {
            "knowledgeBaseQuerySource": {
              "knowledgeBases": [
                "projects/my-project-id/knowledgeBases/my-knowledge-base-id"
              ]
            },
            "maxResults": 3,
            "confidenceThreshold": 0.44
          },
          "conversationModelConfig": {}
        }
      ]
    },
    "messageAnalysisConfig": {}
  },
  "notificationConfig": {
    "topic": "projects/my-project-id/topics/aa-conversation-lifecycle-event",
    "messageFormat": "JSON"
  },
  "newMessageEventNotificationConfig": {
    "topic": "projects/my-project-id/topics/aa-new-message-event",
    "messageFormat": "JSON"
  },
   "newRecognitionResultNotificationConfig": {
    "topic": "projects/my-project/topics/aa-new-recognition-result-notification-event",
    "messageFormat": "JSON"
  },
  "languageCode": "en-US"
}
```

1. Create or select a service account to represent the Pub/Sub subscription identity.

```bash
$ gcloud iam service-accounts create cloud-run-pubsub-invoker \
     --display-name "Cloud Run Pub/Sub Invoker"
```

2. Give the invoker service account permission to invoke your interceptor service.

```bash
gcloud run services add-iam-policy-binding $INTERCEPTOR_SERVICE_NAME \
   --member=serviceAccount:cloud-run-pubsub-invoker@$GCP_PROJECT_ID.iam.gserviceaccount.com \
   --role=roles/run.invoker
```

3. For each Cloud Pub/Sub topic, set the topic id as environment variable `$TOPIC_ID` and create a Pub/Sub subscription with the service account.

```bash
# For new suggestion events
$ export TOPIC_ID='your-new-suggestion-topic-id' && gcloud pubsub subscriptions create $SUBSCRIPTION_NAME --topic $TOPIC_ID \
   --push-endpoint=$INTERCEPTOR_SERVICE_URL/human-agent-assistant-event \
   --push-auth-service-account=cloud-run-pubsub-invoker@$GCP_PROJECT_ID.iam.gserviceaccount.com

# For new message events
$ export TOPIC_ID='your-new-message-event-topic-id' && gcloud pubsub subscriptions create $SUBSCRIPTION_NAME --topic $TOPIC_ID \
   --push-endpoint=$INTERCEPTOR_SERVICE_URL/new-message-event \
   --push-auth-service-account=cloud-run-pubsub-invoker@$GCP_PROJECT_ID.iam.gserviceaccount.com

# For conversation lifecycle events
$ export TOPIC_ID='your-conversation-lifecycle-event-topic' && gcloud pubsub subscriptions create $SUBSCRIPTION_NAME --topic $TOPIC_ID \
   --push-endpoint=$INTERCEPTOR_SERVICE_URL/conversation-lifecycle-event \
   --push-auth-service-account=cloud-run-pubsub-invoker@$GCP_PROJECT_ID.iam.gserviceaccount.com

# For new recognition result notification events
$ export TOPIC_ID='your-new-recognition-result-notification-event-topic' && gcloud pubsub subscriptions create
$SUBSCRIPTION_NAME --topic $TOPIC_ID \
   --push-endpoint=$INTERCEPTOR_SERVICE_URL/new-recognition-result-notification-event \
   --push-auth-service-account=cloud-run-pubsub-invoker@$GCP_PROJECT_ID.iam.gserviceaccount.com
```

# (Optional) Integration with Cloud Build
If you plan to build a continous deployment pipeline for the services, you can integrate Cloud Build triggers for your own repository.

Check an example Cloud Build configuration file at `./cloudbuild.yaml` and related resources:
- [How to create and manage build triggers](https://cloud.google.com/build/docs/automating-builds/create-manage-triggers)
- [Cloud Run - Continuous deployment from Git using Cloud Build](https://cloud.google.com/run/docs/continuous-deployment-with-cloud-build)