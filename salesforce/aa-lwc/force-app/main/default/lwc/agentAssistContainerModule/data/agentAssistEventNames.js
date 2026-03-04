/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const agentAssistEventNames = [
  "active-conversation-selected",
  "copy-to-clipboard",
  "smart-reply-selected",
  "smart-reply-follow-up-suggestions-received",
  "conversation-details-received",
  "conversation-initialization-requested",
  "conversation-initialized",
  "conversation-started",
  "conversation-completed",
  "conversation-profile-requested",
  "conversation-profile-received",
  "conversation-model-requested",
  "conversation-model-received",
  "get-generators-requested",
  "get-generators-received",
  "new-message-received",
  "analyze-content-requested",
  "analyze-content-response-received",
  "conversation-summarization-requested",
  "stateless-suggestion-requested",
  "stateless-suggestion-response-received",
  "stateless-conversation-summarization-requested",
  "stateless-conversation-summarization-response-received",
  "conversation-summarization-received",
  "dialogflow-api-error",
  "dialogflow-api-authentication-error",
  "answer-record-requested",
  "answer-record-received",
  "patch-answer-record-requested",
  "patch-answer-record-received",
  "article-search-requested",
  "article-search-response-received",
  "dark-mode-toggled",
  "snackbar-notification-requested",
  "live-person-connector-initialized",
  "genesys-cloud-connector-initialized",
  "genesys-engage-wwe-connector-initialized",
  "api-connector-initialized",
  "event-based-connector-initialized",
  "live-person-connector-initialization-failed",
  "genesys-cloud-connector-initialization-failed",
  "genesys-engage-wwe-connector-initialization-failed",
  "genesys-cloud-connector-access-token-received",
  "api-connector-initialization-failed",
  "event-based-connector-initialization-failed",
  "event-based-connection-established",
  "list-messages-requested",
  "list-messages-response-received",
  "virtual-agent-assist-response-message-selected",
  "human-agent-transfer-initiated",
  "search-knowledge-requested",
  "search-knowledge-response-received",
  "knowledge-assist-v2-answer-pasted",
  "agent-coaching-response-selected",
  "batch-create-messages-requested",
  "batch-create-messages-response-received",
  "agent-translation-generator-missing",
  "agent-translation-received"
];

export default agentAssistEventNames;
