/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import BasePlatformService from './BasePlatformService';

export default class TwilioFlexPlatformService extends BasePlatformService {
  pollingTimeout = null;

  ////////////////////////////////////////////////////////////////////////////
  // Init & Teardown
  ////////////////////////////////////////////////////////////////////////////

  constructor(lwc, refs) {
    super(lwc, refs);
    this.handleConversationEndedForTwilioFlex = this.handleConversationEndedForTwilioFlex.bind(this);
  }

  async init() {
    // Set up Agent Assist UIM to work with Twilio Flex
    this.lwc.debugLog('initTwilioFlex called');
    this.lwc.conversationName = await this.fetchConversationName(
      this.lwc.contactPhone,
    );
    if (
      !this.lwc.conversationName ||
      (await this.isConversationCompleted(this.lwc.contactPhone))
    ) {
      this.pollForConversationNameByIntegrationKey(this.lwc.contactPhone);
    }
    this.listenToAgentAssistEventsForTwilioFlex();
  }

  teardown() {
    // Clean up Agent Assist UIM Twilio Flex
    super.teardown();
    if (this.pollingTimeout) {
      clearTimeout(this.pollingTimeout);
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // Setup Event Listeners and Subscriptions
  ////////////////////////////////////////////////////////////////////////////

  listenToAgentAssistEventsForTwilioFlex() {
    this.lwc.debugLog('listenToAgentAssistEventsForTwilioFlex called');
    // Handle Agent Assist events
    addAgentAssistEventListener(
      "conversation-completed",
      this.handleConversationEndedForTwilioFlex,
      { namespace: this.lwc.recordId },
    );
  }

  ////////////////////////////////////////////////////////////////////////////
  // Handle Events
  ////////////////////////////////////////////////////////////////////////////

  async fetchConversationName(conversationIntegrationKey, timeout = 5000) {
    // Gets conversationName from Redis using conversationIntegrationKey.
    // Presence intended to trigger UI Module init for CTI add-on based integrations.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(
        this.lwc.endpoint +
           '/conversation-name?conversationIntegrationKey=' +
           conversationIntegrationKey,
        { ...this.createRequestOptions('GET'), signal: controller.signal },
      );

      if (response?.ok) {
        const data = await response.json();
        return data.conversationName;
      } else if (response && response.status !== 404) {
        this.lwc.debugLog(
          `Error fetching conversation name: ${response.status} ${response.statusText}`,
        );
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        // Re-throw the abort error so the poller can catch it and stop.
        throw error;
      } else {
        this.lwc.debugLog(
          `Network error fetching conversation name: ${error.message}`,
        );
      }
    } finally {
      clearTimeout(timeoutId);
    }
    return null;
  }

  async pollForConversationNameByIntegrationKey(
    conversationIntegrationKey,
    {
      initialDelay = 1000,
      maxDelay = 10000,
      requestTimeoutMs = 9900,
    } = {},
  ) {
    // Poll continuously for a conversationName with a backoff.
    // It starts polling rapidly, then cools down to a 10-second interval.
    this.lwc.conversationName = undefined;
    let attempt = 0;

    const poll = async (delayMs) => {
      attempt++;
      this.lwc.debugLog(`Polling for conversationName... (attempt ${attempt}, delay: ${delayMs}ms)`);

      try {
        this.lwc.conversationName = await this.fetchConversationName(
          conversationIntegrationKey,
          requestTimeoutMs,
        );

        if (
          this.lwc.conversationName &&
          !(await this.isConversationCompleted(conversationIntegrationKey))
        ) {
          this.lwc.debugLog(`Found conversationName: ${this.lwc.conversationName}. Initializing UI Modules.`);
          this.handleConnectorInitialized();
          this.initUIModules();
          return; // Stop polling on success
        } else {
          throw new Error('Conversation not found or already completed.'); // Force retry
        }
      } catch (error) {
        this.lwc.debugLog(`Polling attempt ${attempt} failed: ${error.message}`);

        // Calculate the next delay with a linear increase, capped at maxDelay.
        // This reaches maxDelay in ~10 attempts.
        const increment = (maxDelay - initialDelay) / 10;
        const nextDelay = Math.min(maxDelay, delayMs + increment);

        // Schedule the next poll.
        this.pollingTimeout = setTimeout(() => poll(nextDelay), delayMs);
      }
    };

    poll(initialDelay);
  }

  handleConversationEndedForTwilioFlex() {
    // Generate a summary when a Twilio Flex conversation ends
    this.lwc.debugLog("handleConversationEndedForTwilioFlex called");
    if (this.lwc.features.includes("CONVERSATION_SUMMARIZATION")) {
      this.lwc.triggerSummarization();
    }
    this.pollForConversationNameByIntegrationKey(this.lwc.contactPhone);
  }
}
