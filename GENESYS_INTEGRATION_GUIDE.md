# Google Agent Assist & Genesys Cloud Voice Integration Guide

A developer-friendly implementation guide for integrating **Google Cloud Agent Assist** with **Genesys Cloud Voice** and **Salesforce Service Cloud (LWC)**.

---

## 1. Official Documentation & Related References

Before beginning implementation, review the official documentation across Google Cloud, Genesys Cloud, and Salesforce.

### 1.1 Google Cloud Agent Assist & UI Modules
* **[Agent Assist UI Modules Overview](https://cloud.google.com/agent-assist/docs/ui-modules)**: Architecture, features, and deployment options.
* **[UI Modules Managed Container Documentation](https://cloud.google.com/agent-assist/docs/ui-modules-container-documentation)**: Tag attributes, input parameters, and container mounting.
* **[UI Modules Individual Components](https://cloud.google.com/agent-assist/docs/ui-modules-components-documentation)**: Fine-grained component customization (transcripts, smart reply, knowledge assist).
* **[UI Modules Events & Custom Connectors](https://cloud.google.com/agent-assist/docs/ui-modules-events-documentation)**: Registering and dispatching namespaced custom events (`agentAssistEventNames`).
* **[Agent Assist Extended Streaming for Voice](https://cloud.google.com/agent-assist/docs/extended-streaming)**: Dual-channel bi-directional audio streaming with Dialogflow CX.
* **[Conversation Profiles Configuration](https://cloud.google.com/agent-assist/docs/conversation-profile)**: Enabling features, generators, and notification topics.
* **[Cloud Pub/Sub Notifications for Agent Assist](https://cloud.google.com/agent-assist/docs/pub-sub)**: Event schemas for suggestions, lifecycle events, and transcripts.
* **[Dialogflow CX / ES REST API v2beta1 Reference](https://cloud.google.com/dialogflow/es/docs/reference/rest/v2beta1)**: Conversation and suggestion endpoints.

### 1.2 Published Reference Architectures (Comparative Baseline)
* **[Twilio Flex Voice Integration with Salesforce & Agent Assist](https://cloud.google.com/agent-assist/docs/twilio-flex-voice)**: The primary published reference architecture for voice desktop integrations. *(See [Section 2.2](#22-architectural-comparison-genesys-cloud-vs-twilio-flex-voice) for key architectural differences).*
* **[Salesforce Agent Assist LWC Integration Guide](https://cloud.google.com/agent-assist/docs/salesforce)**: Native Lightning Web Component embedding in Salesforce Service Console.
* **[Genesys Cloud Application Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-app)**: Embedding Agent Assist inside Genesys Cloud web messaging and chat.
* **[Genesys Cloud Voice Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)**: Cloud-to-cloud voice streaming via AudioHook.

### 1.3 Genesys Cloud & Open CTI Documentation
* **[Genesys Cloud AudioHook Protocol Specification](https://developer.genesys.cloud/devapps/audiohook/)**: WebSocket framing, audio format (PCM 8kHz/16kHz), and payload contracts.
* **[Genesys Cloud AudioHook Monitor Overview](https://help.genesys.cloud/articles/about-audiohook-monitor/)**: Installing and attaching AudioHook to ACD Queues.
* **[Genesys Cloud CTI Adapter for Salesforce](https://docs.genesys.com/Documentation/CCTI/latest/SUG/Welcome)**: Installing and managing the Salesforce Open CTI managed package.
* **[Generate Contact Center Configuration XML File](https://help.genesys.cloud/articles/generate-contact-center-configuration-xml-file/)**: Open CTI Call Center definition schema.
* **[Configure Remote Site Settings in Salesforce](https://help.genesys.cloud/articles/configure-remote-site-settings-in-salesforce/)**: Required Genesys Cloud regional endpoint whitelist.

---

## 2. Overview & Architecture

This integration bridges real-time voice conversations from Genesys Cloud to Google Cloud Agent Assist, streaming dual-channel audio via Genesys AudioHook to Dialogflow CX, and presenting contextual AI suggestions (summarization, knowledge search, generative answers, smart replies) inside Salesforce Service Console or the Genesys Cloud Interaction Widget.

### 2.1 System Architecture Diagram

```
+-----------------------------------------------------------------------------------------------+
|                                       GENESYS CLOUD                                           |
|                                                                                               |
|   +--------------------------+                         +----------------------------------+   |
|   |  Architect Inbound Flow  | --> Transfer to ACD --> | ACD Voice Queue (DID Mapping)    |   |
|   +--------------------------+                         +----------------------------------+   |
|                                                                         |                     |
|                                                   +---------------------+-----------------+   |
|                                                   | AudioHook Monitor Integration         |   |
|                                                   +---------------------------------------+   |
+-------------------------------------------------------|---------------------------------------+
                                                        | Dual-channel PCM streaming (WSS)
                                                        v
+-----------------------------------------------------------------------------------------------+
|                                    GOOGLE CLOUD PLATFORM                                      |
|                                                                                               |
|   +---------------------------------------------------------------------------------------+   |
|   | AudioHook Voice Interceptor (Cloud Run)                                               |   |
|   | (wss://${AUDIOHOOK_SERVICE_URL}/connect)                                              |   |
|   +---------------------------------------------------------------------------------------+   |
|         |                                                           |                         |
|         | 1. Bi-directional Dialogflow CX Streaming                 | 2. Maps Genesys UUID -> |
|         v                                                           |    DFCX Conversation    |
|   +--------------------------------------------------+              v                         |
|   | Dialogflow CX / Agent Assist Engine              |     +------------------------------+   |
|   | Profile: .../conversationProfiles/${PROFILE_ID}  |     | Memorystore Redis            |   |
|   +--------------------------------------------------+     | (${REDIS_HOST}:${REDIS_PORT})|   |
|         |                                                  +------------------------------+   |
|         | Pub/Sub Events (Suggestions, Lifecycle, etc.)             ^                         |
|         v                                                           |                         |
|   +--------------------------------------------------+              | Query / Cache Lookup    |
|   | Cloud Pub/Sub Interceptor (Cloud Run)            |              |                         |
|   +--------------------------------------------------+--------------+                         |
|         | Socket.IO Notifications                                                             |
|         v                                                                                     |
|   +---------------------------------------------------------------------------------------+   |
|   | UI Connector / Proxy Server (Cloud Run)                                               |   |
|   | (https://${UI_CONNECTOR_SERVICE_URL})                                                 |   |
|   +---------------------------------------------------------------------------------------+   |
|         ^                                                           ^                         |
+---------|-----------------------------------------------------------|-------------------------+
          | Auth Token Exchange & Suggestions                         | Live Suggestions
          v                                                           v
+---------------------------------------------------+   +---------------------------------------+
| Salesforce Service Console (Open CTI / LWC)       |   | Genesys Cloud Desktop (Widget)        |
| - Genesys Cloud for Salesforce CTI                |   | - Interaction Widget                  |
| - Google Agent Assist LWC Module                  |   |   (Frontend Web App)                  |
+---------------------------------------------------+   +---------------------------------------+
```

### 2.2 Architectural Comparison: Genesys Cloud vs. Twilio Flex Voice

| Dimension | Twilio Flex Voice Pattern | Genesys Cloud Voice Pattern (This Guide) |
| :--- | :--- | :--- |
| **Audio Ingestion** | Twilio Media Streams (WebSocket to gRPC proxy) | Genesys AudioHook Monitor (WebSocket dual-channel PCM) |
| **Session Key Identification** | `CallSid` / Twilio Task SID | Genesys Conversation UUID (`interaction.id` / `gcConversationId`) |
| **CTI Client in Salesforce** | Twilio Flex React Plugin / Canvas | Genesys Cloud Open CTI Adapter (`04tQp...` v2.33.0) |
| **Interaction Discovery** | Twilio TaskRouter sync event listener | Multi-tiered: `postMessage` CTI ping + Shared Storage + Apex fallback (`Task.CallObject`) |
| **Agent Desktop Target** | Twilio Flex standalone UI or Salesforce CTI | Salesforce Service Console LWC or Genesys Interaction Widget |

---

## 3. Prerequisites & Environment Setup

### 3.1 Required Tools
* [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install-sdk) `>= 480.0.0`
* [Salesforce CLI (`sf`)](https://developer.salesforce.com/tools/salesforcecli) `>= 2.0.0`
* [Node.js & npm](https://nodejs.org/) `>= 18.x`
* Python `>= 3.10`

### 3.2 Google Cloud IAM Roles
Ensure your deployment identity has the following roles:
* `roles/resourcemanager.projectIamAdmin`
* `roles/serviceusage.serviceUsageAdmin`
* `roles/iam.serviceAccountAdmin` & `roles/iam.serviceAccountUser`
* `roles/pubsub.admin`
* `roles/secretmanager.admin`
* `roles/run.admin`
* `roles/redis.admin`
* `roles/vpcaccess.admin`
* `roles/dialogflow.agentAssistClient`

### 3.3 Environment Variable Template

Copy and save as `.env` before running deployment scripts:

```bash
# ==========================================
# Google Cloud Configuration
# ==========================================
export GCP_PROJECT_ID="<your-gcp-project-id>"
export SERVICE_REGION="us-central1"
export RESOURCE_PREFIX="aa"
export NAMESPACE="<your-environment-prefix>" # e.g. dev, staging, prod, v1

# Cloud Pub/Sub Topic Identifiers
export AGENT_ASSIST_NOTIFICATIONS_TOPIC_ID="${RESOURCE_PREFIX}-new-suggestion-topic-${NAMESPACE}"
export NEW_MESSAGE_NOTIFICATIONS_TOPIC_ID="${RESOURCE_PREFIX}-new-message-topic-${NAMESPACE}"
export CONVERSATION_LIFECYCLE_NOTIFICATIONS_TOPIC_ID="${RESOURCE_PREFIX}-conversation-event-topic-${NAMESPACE}"
export NEW_RECOGNITION_RESULT_NOTIFICATION_TOPIC_ID="${RESOURCE_PREFIX}-intermediate-transcript-topic-${NAMESPACE}"

# Cloud Pub/Sub Subscription Identifiers
export AGENT_ASSIST_NOTIFICATIONS_SUBSCRIPTION_ID="${RESOURCE_PREFIX}-new-suggestion-sub-${NAMESPACE}"
export NEW_MESSAGE_NOTIFICATIONS_SUBSCRIPTION_ID="${RESOURCE_PREFIX}-new-message-sub-${NAMESPACE}"
export CONVERSATION_LIFECYCLE_NOTIFICATIONS_SUBSCRIPTION_ID="${RESOURCE_PREFIX}-conversation-event-sub-${NAMESPACE}"
export NEW_RECOGNITION_RESULT_NOTIFICATION_SUBSCRIPTION_ID="${RESOURCE_PREFIX}-intermediate-transcript-sub-${NAMESPACE}"

# Dialogflow CX Conversation Profile Path
export CONVERSATION_PROFILE_NAME="projects/${GCP_PROJECT_ID}/locations/global/conversationProfiles/<your-conversation-profile-id>"

# Infrastructure Configuration
export REDIS_INSTANCE_ID="${RESOURCE_PREFIX}-redis-${NAMESPACE}"
export VPC_CONNECTOR_NAME="${RESOURCE_PREFIX}-vpc-${NAMESPACE}"
export REDIS_IP_RANGE="10.8.0.0/28" # Ensure non-overlapping CIDR block

# ==========================================
# Genesys Cloud Configuration
# ==========================================
export GENESYS_CLOUD_ORG_NAME="<your-genesys-org-name>"
export GENESYS_CLOUD_REGION="usw2.pure.cloud" # e.g., usw2.pure.cloud, mypurecloud.com
export GENESYS_CLOUD_ENVIRONMENT="usw2.pure.cloud"
export GENESYS_OAUTH_CLIENT_ID="<your-genesys-oauth-client-id>"
export GENESYS_OAUTH_CLIENT_SECRET="<your-genesys-oauth-client-secret>"
export AUDIOHOOK_CREDENTIAL_ID="<your-audiohook-credential-id>"
export AUDIOHOOK_API_KEY="<your-audiohook-shared-api-key>"

# ==========================================
# Salesforce Configuration
# ==========================================
export AUTH_OPTION="SalesforceLWC"
export SALESFORCE_DOMAIN="<your-org-domain>.my.salesforce.com" # Exclude https://
export SALESFORCE_ORGANIZATION_ID="<your-salesforce-org-id>"
export SF_CONNECTED_APP_CONSUMER_KEY="<your-connected-app-client-id>"
export SF_CONNECTED_APP_CONSUMER_SECRET="<your-connected-app-client-secret>"
```

---

## 4. Step-by-Step Implementation

### Phase 1: Google Cloud Infrastructure & Conversation Profile

1. **Enable Google Cloud APIs**:
   ```bash
   gcloud services enable \
     dialogflow.googleapis.com \
     pubsub.googleapis.com \
     run.googleapis.com \
     secretmanager.googleapis.com \
     compute.googleapis.com \
     vpcaccess.googleapis.com \
     redis.googleapis.com
   ```

2. **Create Conversation Profile in Dialogflow CX / Agent Assist Console**:
   * Navigate to **Agent Assist > Conversation Profiles**.
   * Enable desired features:
     * Summarization (`CONVERSATION_SUMMARIZATION`)
     * Knowledge Search (`KNOWLEDGE_SEARCH` / `GENERATIVE_KNOWLEDGE_ASSIST`)
     * Smart Reply (`SMART_REPLY`)
   * Under **Pub/Sub Notification Settings**, link the following topics:
     * Suggestions Event: `projects/${GCP_PROJECT_ID}/topics/${AGENT_ASSIST_NOTIFICATIONS_TOPIC_ID}`
     * Lifecycle Event: `projects/${GCP_PROJECT_ID}/topics/${CONVERSATION_LIFECYCLE_NOTIFICATIONS_TOPIC_ID}`
     * New Message Event: `projects/${GCP_PROJECT_ID}/topics/${NEW_MESSAGE_NOTIFICATIONS_TOPIC_ID}`
     * Intermediate Transcripts: `projects/${GCP_PROJECT_ID}/topics/${NEW_RECOGNITION_RESULT_NOTIFICATION_TOPIC_ID}`

> [!NOTE]
> **Profile Immutability**: Dialogflow CX captures an immutable snapshot (`initialConversationProfile`) when each conversation starts. Updates to profile topics only affect conversations started after the change.

3. **Deploy Memorystore Redis & Serverless VPC Access Connector**:
   ```bash
   # Create Memorystore Redis
   gcloud redis instances create ${REDIS_INSTANCE_ID} \
     --size=5 \
     --region=${SERVICE_REGION}

   # Create Serverless VPC Connector
   gcloud compute networks vpc-access connectors create ${VPC_CONNECTOR_NAME} \
     --network=default \
     --region=${SERVICE_REGION} \
     --range=${REDIS_IP_RANGE}
   ```

---

### Phase 2: Deploy Backend Services (UI Connector & Pub/Sub Interceptor)

1. **Deploy UI Connector (`ui-connector`)**:
   ```bash
   cd aa-integration-backend
   sh ./deploy.sh
   ```
   * The UI Connector exposes endpoints for JWT registration, token refresh, and Dialogflow API proxying.
   * Service URL: `https://${CONNECTOR_SERVICE_NAME}-${PROJECT_NUMBER}.${SERVICE_REGION}.run.app`

2. **Verify Pub/Sub Push Subscriptions**:
   * Ensure push subscriptions target the `cloud-pubsub-interceptor` service endpoint with Cloud Run invoker permissions.

---

### Phase 3: Deploy AudioHook Voice Interceptor

The AudioHook Interceptor receives dual-channel WebSockets from Genesys Cloud, streams bi-directional audio to Dialogflow CX via gRPC, and caches session mappings in Redis.

1. **Configure Environment**:
   ```bash
   cd genesyscloud/genesyscloud-audiohook
   cp .env.example .env
   ```

2. **Deploy to Cloud Run**:
   ```bash
   sh ./deploy.sh
   ```
   * Deployed endpoint: `wss://${AUDIOHOOK_SERVICE_NAME}-${PROJECT_NUMBER}.${SERVICE_REGION}.run.app/connect`

---

### Phase 4: Genesys Cloud Configuration

#### 4.1 Create OAuth Client
1. In Genesys Cloud Admin, navigate to **Integrations > OAuth**.
2. Click **Add Client**:
   * **App Name**: `Google Agent Assist Frontend`
   * **Grant Types**: `Code Authorization` (and/or `Client Credentials`)
   * **Authorized Redirect URIs**: `https://${FRONTEND_SERVICE_URL}`
   * **Scope**: `conversation`, `user-basic-info`, `analytics`.

#### 4.2 Install & Configure AudioHook Monitor
1. Navigate to **Admin > Integrations > Integrations** and install **AudioHook Monitor**.
2. Name: `[CNP] AudioHook Monitor`.
3. On the **Configuration > Properties** tab:
   * **Channel**: `both`
   * **Connection URI**: `wss://${AUDIOHOOK_SERVICE_URL}/connect`
4. On the **Credentials** tab:
   * Provide the configured `AUDIOHOOK_API_KEY` matching Cloud Run environment.
5. Set status to **Active**.

#### 4.3 Attach AudioHook to ACD Voice Queue
1. Navigate to **Admin > Contact Center > Queues**.
2. Select your target voice queue (e.g., `Agent Assist Voice Queue`).
3. Click the **Voice** tab.
4. Under **AudioHook**, select your configured `AudioHook Monitor` integration.
5. Save changes.

#### 4.4 Configure Architect Inbound Flow & DID Mapping
1. In **Architect**, create or edit your **Inbound Call Flow**.
2. Add a **Transfer to ACD** node targeting your Agent Assist Voice Queue.
3. Publish the flow.
4. In **Admin > Routing > Call Routing**, assign your inbound DID phone number to this flow.

#### 4.5 (Optional) Deploy Interaction Widget
1. In **Admin > Integrations > Interaction Widget**, set:
   * **Application URL**:
     ```
     https://${FRONTEND_SERVICE_URL}?conversationId={{gcConversationId}}&gcHostOrigin={{gcHostOrigin}}&gcTargetEnv={{gcTargetEnv}}
     ```
   * **Iframe Sandbox**: `allow-scripts,allow-same-origin,allow-forms,allow-modals,allow-popups`
   * **Permissions Policy**: `clipboard-write,microphone,display-capture`

#### 4.6 User Provisioning & WebRTC Telephony Setup
When onboarding agents or demo users in Genesys Cloud:
1. **User Account Creation**:
   * Navigate to **Admin > Directory > Users** (`+ Add User`) and create the user account with company email.
2. **Assign Required Roles**:
   * Open User > **Roles** tab and assign:
     * `Agent` (or Contact Center Agent)
     * `Communicate - User` (or PureCloud User)
   * *(Grants Telephony, Call Make/Accept, and Queue Join permissions).*
3. **WebRTC Phone Assignment**:
   * Navigate to **Admin > Telephony > Phone Management** (or edit User > **Phone** tab).
   * Assign a **Genesys Cloud WebRTC Phone** to enable browser softphone audio streaming without physical desk phone hardware.
4. **Queue & Group Memberships**:
   * Go to **Admin > Contact Center > Queues > `${TARGET_QUEUE}` > Members** and add the user.
   * Go to **Admin > Directory > Groups > `${TARGET_GROUP}` > Members** and add the user.

---

### Phase 5: Salesforce DX & Open CTI Setup

#### 5.1 Install Genesys Cloud Open CTI Package
* **Package ID**: `04tQp000000ngyzIAA` (`CX Cloud from Genesys and Salesforce` v2.33.0)
* Command:
  ```bash
  sf package install --package 04tQp000000ngyzIAA --wait 15 --target-org <target-org-alias>
  ```

#### 5.2 Deploy Remote Site Settings & CSP Trusted Sites
```bash
cd salesforce/aa-lwc
sf project deploy start --metadata RemoteSiteSetting CspTrustedSite CorsWhitelistOrigin --target-org <target-org-alias>
```

#### 5.3 Configure Call Center Definition & User Assignment
1. Deploy `GenesysCloud.callCenter-meta.xml` or import `GenesysCloudCallCenter.xml`.
2. Assign the Call Center definition to your agent / admin user:
  ```bash
  sf apex run --file scripts/apex/create_callcenter.apex --target-org <target-org-alias>
  ```

#### 5.4 Configure Softphone Layouts & Screen Pop
> [!IMPORTANT]
> Scratch orgs and new Service Cloud instances do not assign a Softphone Layout by default. Without explicit assignment, Open CTI `searchAndScreenPop` calls fail silently.

1. Navigate to **Setup > Feature Settings > Service > Call Center > Softphone Layouts > Softphone Layout Assignment**.
2. Assign **`Standard Softphone Layout`** to your target agent profiles (`System Administrator`, `Custom Support Agent`).
3. Edit the layout to configure screen pop behavior:
   * **Objects to Search**: `Contact`, `Account`, `Lead`, `Case`
   * **Single-matching record**: `Pop detail page`
   * **No matching records**: `Pop to search page` (or `New Case`)

#### 5.5 Configure Agent Assist LWC on Case Record Page
1. Open **Service Console**, navigate to any **Case record**, and select **Edit Page** (Lightning App Builder).
2. Drag the **`agentAssistContainerModule`** component onto the right sidebar.
3. Configure component properties:

| Property | Description | Example Value |
| :--- | :--- | :--- |
| **UI Connector Endpoint** | Cloud Run URL of the UI Connector | `https://${UI_CONNECTOR_SERVICE_URL}` |
| **Conversation Profile** | Full Dialogflow CX Profile Resource Path | `projects/${PROJECT_ID}/locations/global/conversationProfiles/${PROFILE_ID}` |
| **Channel** | Communication channel | `voice` |
| **Platform** | Desktop CTI platform | `genesyscloud` |
| **Connected App Consumer Key** | Salesforce External Client App Client ID | `${SF_CONNECTED_APP_CONSUMER_KEY}` |
| **Connected App Consumer Secret**| Salesforce External Client App Secret | `${SF_CONNECTED_APP_CONSUMER_SECRET}` |
| **Container Height** | CSS height for suggestions panel | `530px` |
| **Show Dark Mode Toggle** | Enables dark/light theme switch | `true` |
| **Show Header** | Shows suggestions header bar | `true` |
| **Show Correctness Feedback** | Displays thumbs up/down agent feedback | `true` |

---

### Phase 6: Automated User Onboarding & Coworker Demo Runbook

#### 6.1 Automated CLI Onboarding Wizard
To streamline developer and tester setup, use the interactive CLI helper:
```bash
# Inside salesforce/aa-lwc
npm run onboard
# Or directly:
python3 scripts/onboard_demo_user.py
```

The CLI automates:
1. **Salesforce Scratch Org User Creation**: Creates a user with unique credentials and generates a 1-click frontdoor login URL.
2. **Permission & CTI Setup**: Runs `create_callcenter.apex` and `setup_omnichannel.apex` against the target org.
3. **Genesys Cloud Provisioning Checklist**: Automatically opens the Genesys Cloud Admin Console in the browser and guides through User, WebRTC Phone, and Queue assignments.
4. **Coworker Demo Runbook Generation**: Exports a ready-to-share Markdown runbook to `~/COWORKER_DEMO_RUNBOOK.md`.
5. **Diagnostics & Health Check**: Validates SF CLI, Cloud Run UI Connector reachability, and scratch org status.

---

#### 6.2 Coworker / Presenter Demo Runbook

##### 1. Salesforce Login
* **URL**: Scratch Org Frontdoor / `https://test.salesforce.com`
* **App**: Open **Service Console** from the App Launcher (9 dots in top-left).

##### 2. Browser Pop-up & Microphone Permissions (CRITICAL)
1. In Chrome address bar, click the **Site Settings / Lock / Tune** icon.
2. Ensure **Pop-ups and redirects** is set to **Always allow** for:
   * `https://*.scratch.lightning.force.com` (or `https://*.salesforce.com`)
   * `https://*.pure.cloud` (or `https://*.mypurecloud.com`)
3. Ensure **Microphone** permission is set to **Allow**.

##### 3. Genesys CTI Softphone Login & Presence
1. In the bottom utility bar of Service Console, click **Genesys CTI Softphone**.
2. Log in with your Genesys Cloud credentials.
3. In the top-right corner of the softphone panel, toggle status to **On Queue**.
4. Verify the queue toggle switch is enabled.

##### 4. Live Call Execution & Agent Assist
1. Dial the inbound demo phone number mapped to the ACD queue.
2. Softphone rings -> accept call -> Salesforce auto-screen-pops the Case record.
3. Google Agent Assist (`agentAssistContainerModule`) on the right sidebar binds the conversation session in 1–3 seconds.
4. Speak customer and agent dialogue to observe real-time speech-to-text transcripts, generative smart replies, knowledge assist cards, and summarization.

##### 5. After Call Work (ACW)
* After hanging up, **select a wrap-up code and complete ACW** in the CTI softphone to restore agent status back to **On Queue**.

---

## 5. End-to-End Verification Checklist

| Step | Action | Expected Result | Status |
| :---: | :--- | :--- | :---: |
| 1 | Run LWC Unit Tests | `npm test` passes all Jest test suites (113/113 passing) | [ ] |
| 2 | Check Cloud Run Health | UI Connector and AudioHook return HTTP 200/404 health status | [ ] |
| 3 | Log in to Genesys CTI Softphone | Softphone renders in Service Console utility bar and authenticates | [ ] |
| 4 | Set Agent Status | Toggle agent switch to **On Queue**; clear any pending ACW | [ ] |
| 5 | Place Inbound Test Call | DID routes through Architect -> rings in CTI Softphone | [ ] |
| 6 | Verify AudioHook Stream | Cloud Run logs show WebSocket `open` and bi-directional audio frames | [ ] |
| 7 | Verify Session Discovery | LWC captures `interaction.id`, polls `/conversation-name`, binds session | [ ] |
| 8 | Validate Real-Time Suggestions | Suggestions, summaries, and smart replies appear in real-time in LWC | [ ] |

---

## 6. Walkthrough Gaps & Troubleshooting Playbook

### 6.1 Session Discovery Handshake & Race Condition
* **The Gap**: When an incoming call triggers a screen pop, the Case record page loads and mounts the LWC immediately. At that exact millisecond, AudioHook may still be completing its SIP/WebRTC handshake and creating the Dialogflow CX conversation.
* **Resolution**: The LWC uses `GenesysCloudPlatformService.js` with exponential backoff polling (`GET /conversation-name?conversationIntegrationKey=<UUID>`) and cross-tab storage caching. HTTP 404 responses during the first 1–3 seconds are expected while the session is provisioned.

### 6.2 Browser Pop-up Blocker for WebRTC Phone
* **The Gap**: Genesys CTI Softphone spawns a detached helper window for WebRTC audio streams (`The WebRTC Phone window is unable to display`). Modern browsers block this by default on scratch org domains.
* **Resolution**: In Chrome address bar, click the Pop-up Blocker icon and select **Always allow pop-ups and redirects** from `https://*.lightning.force.com` and `https://*.pure.cloud`. Grant microphone access.

### 6.3 Angular ZoneJS & Lightning Web Security (LWS)
* **The Gap**: UI Modules (`container.js`) use Angular ZoneJS to wrap browser event listeners, which conflicts with Salesforce Lightning Web Security / Locker service DOM virtualization.
* **Resolution**: Declare `window.__Zone_disable_on_property = true;` at the top of the LWC JavaScript file before UI module scripts load.

### 6.4 Missing Softphone Layout in Scratch Orgs
* **The Gap**: Fresh scratch orgs do not assign a Softphone Layout by default, causing Open CTI `searchAndScreenPop` calls to fail silently without opening the Case record.
* **Resolution**: Explicitly assign **`Standard Softphone Layout`** to **`System Administrator`** under **Setup > Softphone Layout Assignment**.

### 6.5 After Call Work (ACW) Blocking Incoming Calls
* **The Gap**: If a test call ends and the agent does not close the ACW wrap-up code in the CTI softphone, the agent status remains busy and subsequent test calls will not ring.
* **Resolution**: Ensure agents complete ACW wrap-up after each test call to return to the active `On Queue` state.

### 6.6 Multi-Tab Event Namespacing
* **The Gap**: In Salesforce Service Console, agents work across multiple tabs simultaneously. Without event isolation, suggestions for Call A bleed into Call B's tab.
* **Resolution**: Dispatch and listen to all Agent Assist events with `{ namespace: this.recordId }` or `{ namespace: conversationId }`.
