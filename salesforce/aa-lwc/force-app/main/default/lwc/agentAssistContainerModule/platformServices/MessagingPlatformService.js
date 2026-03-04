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

import {
  APPLICATION_SCOPE,
  subscribe,
  unsubscribe,
  MessageContext
} from "lightning/messageService";

import conversationAgentSendChannel from "@salesforce/messageChannel/lightning__conversationAgentSend";
import conversationEndUserMessageChannel from "@salesforce/messageChannel/lightning__conversationEndUserMessage";
import conversationEndedChannel from "@salesforce/messageChannel/lightning__conversationEnded";
import tabClosedChannel from "@salesforce/messageChannel/lightning__tabClosed";

import BasePlatformService from './BasePlatformService';

export default class MessagingPlatformService extends BasePlatformService {
  subscriptions = [];

  ////////////////////////////////////////////////////////////////////////////
  // Init & Teardown
  ////////////////////////////////////////////////////////////////////////////

  init() {
    // Set up Agent Assist UIM to work with Messaging for In-App and Web
    this.generateConversationName();
    this.subscribeToMessageChannels();
    this.listenToAgentAssistEventsForMessaging();
  }

  teardown() {
    super.teardown();
    // Clean up Agent Assist UIM Messaging for In-App and Web
    this.unsubscribeFromMessagingChannels();
  }

  ////////////////////////////////////////////////////////////////////////////
  // Setup Event Listeners and Subscriptions
  ////////////////////////////////////////////////////////////////////////////

  listenToAgentAssistEventsForMessaging() {
    // Handle Agent Assist events
    addAgentAssistEventListener(
      "smart-reply-selected",
      (event) =>
        this.handleAgentAssistEventForMessaging("smart-reply-selected", event),
      { namespace: this.lwc.recordId }
    );
    addAgentAssistEventListener(
      "agent-coaching-response-selected",
      (event) =>
        this.handleAgentAssistEventForMessaging(
          "agent-coaching-response-selected",
          event,
        ),
      { namespace: this.lwc.recordId }
    );
  }

  subscribeToMessageChannels() {
    // Attach handler functions to Messaging events
    this.subscriptions.push(
      subscribe(
        this.lwc.messageContext,
        conversationAgentSendChannel,
        (event) => this.handleMessageSendForMessaging('HUMAN_AGENT', event),
        { scope: APPLICATION_SCOPE },
      ),
    );
    this.subscriptions.push(
      subscribe(
        this.lwc.messageContext,
        conversationEndUserMessageChannel,
        (event) => this.handleMessageSendForMessaging('END_USER', event),
        { scope: APPLICATION_SCOPE },
      ),
    );
    this.subscriptions.push(
      subscribe(
        this.lwc.messageContext,
        conversationEndedChannel,
        (event) => this.handleConversationEndedForMessaging(event),
        { scope: APPLICATION_SCOPE },
      ),
    );
    this.subscriptions.push(
      subscribe(
        this.lwc.messageContext,
        tabClosedChannel,
        (event) => this.handleTabClosedForMessaging(event),
        { scope: APPLICATION_SCOPE },
      ),
    );
  }

  unsubscribeFromMessagingChannels() {
    // Detach handler functions from Messaging events
    this.subscriptions.forEach((sub) => {
      unsubscribe(sub);
    });
    this.subscriptions = [];
  }

  ////////////////////////////////////////////////////////////////////////////
  // Handle Events
  ////////////////////////////////////////////////////////////////////////////

  handleMessageSendForMessaging(senderRole, message) {
    // Send new Messaging messages to the UI Connector
    if (this.lwc.recordId !== message.recordId) return;
    dispatchAgentAssistEvent(
      "analyze-content-requested",
      {
        detail: {
          conversationId: this.lwc.conversationId,
          participantRole: senderRole,
          request: {
            textInput: { text: message.content, languageCode: "us" }
          }
        }
      },
      { namespace: this.lwc.recordId }
    );
  }

  async handleAgentAssistEventForMessaging(eventName, event) {
    // Handle Agent Assist events
    if (eventName === "agent-coaching-response-selected") {
      // Handle Agent Coaching response selection
      await this.refs.conversationToolkitApi.setAgentInput(this.lwc.recordId, {
        text: event.detail.selectedResponse
      });
    } else if (eventName === "smart-reply-selected") {
      // Handle Smart Reply selection by the agent
      await this.refs.conversationToolkitApi.setAgentInput(this.lwc.recordId, {
        text: event.detail.answer.reply
      });
    }
  }

  generateConversationName() {
    // Generate a Dialogflow conversation name.
    // Works when the Dialogflow conversation isn't created outside SF.
    let prefix = this.lwc.projectLocationName;
    this.lwc.conversationId = `SF-${this.lwc.recordId}`;
    this.lwc.conversationName = `${prefix}/conversations/${this.lwc.conversationId}`;
    this.lwc.debugLog(`this.lwc.conversationName - ${this.lwc.conversationName}`);
  }

  handleConversationEndedForMessaging(event) {
    // Generate a summary when a Messaging conversation ends
    this.lwc.debugLog("handleConversationEnded called");

    if (this.lwc.recordId !== event.recordId) return;
    if (this.lwc.features.includes("CONVERSATION_SUMMARIZATION")) {
      dispatchAgentAssistEvent(
        "conversation-completed",
        { detail: { conversationName: this.lwc.conversationName } },
        { namespace: this.lwc.recordId }
      );

      // Give handleTabClosed opportunity to cancel summarization
      this.lwc.cancelSummarizationTimeout = setTimeout(() => {
        // Create a synthetic click event to trigger summarization modal
        this.lwc.triggerSummarization();
      }, 500);
    }
  }

  handleTabClosedForMessaging(event) {
    // Handle Messaging Session tab closed event
    this.lwc.debugLog("handleTabClosed called");
    // Cancel summarization if the tab is closing
    if (this.lwc.cancelSummarizationTimeout) {
      clearTimeout(this.lwc.cancelSummarizationTimeout);
    }
  }
}
