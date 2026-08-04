/**
 * Copyright 2026 Google LLC
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

// This logging function for all Agent Assist Events is useful for client side debugging.
// It should be disabled in production.
// https://docs.cloud.google.com/agent-assist/docs/ui-modules-events-documentation

const eventNames = [
  "active-conversation-selected",
  "api-connector-initialized",
  "smart-reply-selected",
  "smart-reply-follow-up-suggestions-received",
  "conversation-details-received",
  "conversation-initialization-requested",
  "conversation-initialized",
  "conversation-started",
  "conversation-completed",
  "conversation-profile-requested",
  "conversation-profile-received",
  "new-message-received",
  "analyze-content-requested",
  "analyze-content-response-received",
  "conversation-summarization-requested",
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
  "api-connector-initialization-failed",
  "event-based-connector-initialized",
  "event-based-connector-initialization-failed",
  "event-based-connection-established",
  "list-messages-requested",
  "list-messages-response-received",
  "human-agent-transfer-initiated",
  "search-knowledge-requested",
  "search-knowledge-response-received",
  "knowledge-assist-v2-answer-pasted"
];

eventNames.forEach((eventName) => {
  const params = new URLSearchParams(window.location.search);
  const callId = params.get("call_id") || "";
  addAgentAssistEventListener(
    eventName,
    (event) => {
      console.debug(eventName, event);
    }
  );
});
