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

import agentAssistEventNames from "../data/agentAssistEventNames";
import sampleContext from "../data/sampleContext";
import {
  DIALOGFLOW_API_VERSION,
  TOKEN_EXPIRATION_THRESHOLD_SEC,
  TOKEN_WAIT_INTERVAL_MS,
  TOKEN_HEALTHY_LOG_INTERVAL_MS,
  POLL_MAX_RETRIES,
  POLL_INITIAL_DELAY_MS,
  POLL_DELAY_INCREMENT_MS
} from "../config";

let lastTokenHealthyLogTimeMs = 0;

export default class BasePlatformService {
  lwc;
  refs = {};

  constructor(lwc, refs = {}) {
    this.lwc = lwc;
    this.refs = refs;
  }

  init() {
    // Base initialization logic, can be overridden by subclasses
  }

  teardown() {
    // Base teardown logic, can be overridden by subclasses
  }

  ////////////////////////////////////////////////////////////////////////////
  // AUTH & INIT UI MODULES
  ////////////////////////////////////////////////////////////////////////////

  async registerAuthToken() {
    // Get a UI Connector auth token using a SF External Client App id token.
    const access_token = await fetch(
      `/services/oauth2/token?` +
        new URLSearchParams({
          grant_type: "client_credentials",
          client_id: this.lwc.consumerKey,
          client_secret: this.lwc.consumerSecret
        })
    )
      .then((res) => {
        if (!res.ok)
          throw new Error(`OAuth token request failed: ${res.statusText}`);
        return res.json();
      })
      .then((data) => data.access_token)
      .catch((err) => {
        console.error("Failed to register auth token:", err);
        this.lwc.loadError = err;
        return null;
      });
    this.lwc.debugLog(
      `Salesforce External Client App OAuth Token successfully retrieved.`
    );

    if (!access_token) {
      return null;
    }

    return await fetch(this.lwc.endpoint + "/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access_token}`
      }
    })
      .then((res) => {
        if (!res.ok)
          throw new Error(
            `UI Connector registration failed: ${res.statusText}`
          );
        return res.json();
      })
      .then((data) => {
        this.lwc.debugLog(`UI Modules JWT Token successfully retrieved.`);
        return data.token;
      })
      .catch((err) => {
        console.error("Failed to get UI Connector token:", err);
        this.lwc.loadError = err;
        return null;
      });
  }

  async checkAndRefreshToken() {
    try {
      if (!this.lwc.token) return;
      const payloadBase64Url = this.lwc.token.split(".")[1];
      const base64 = payloadBase64Url.replace(/-/g, "+").replace(/_/g, "/");
      const binaryString = atob(base64);

      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const jsonPayload = new TextDecoder().decode(bytes);
      const payload = JSON.parse(jsonPayload);

      if (payload && payload.exp) {
        const currentTimeSec = Math.floor(Date.now() / 1000);
        const timeUntilExpSec = payload.exp - currentTimeSec;

        // Refresh if token is within 1 minute (60s) of expiring
        if (timeUntilExpSec < TOKEN_EXPIRATION_THRESHOLD_SEC) {
          this.lwc.debugLog(
            `Token is expiring in ${timeUntilExpSec}s (threshold ${TOKEN_EXPIRATION_THRESHOLD_SEC}s). Refreshing...`
          );
          this.lwc.token = await this.registerAuthToken();
          if (this.connector) {
            this.connector.setAuthToken(this.lwc.token);
            this.lwc.debugLog(
              "Auth token successfully updated on UiModulesConnector instance."
            );
          }
        } else {
          const currentTimeMs = Date.now();
          if (
            currentTimeMs - lastTokenHealthyLogTimeMs >=
            TOKEN_HEALTHY_LOG_INTERVAL_MS
          ) {
            this.lwc.debugLog(
              `Token is healthy. Expires in ${timeUntilExpSec}s.`
            );
            lastTokenHealthyLogTimeMs = currentTimeMs;
          }
        }
      }
    } catch (err) {
      this.lwc.debugLog(
        `Failed to dynamically verify token expiration: ${err.message}.`
      );
    }
  }

  initUIModules() {
    this.lwc.debugLog("initUIModules called");

    // Create Transcript UI Module.
    if (this.lwc.showTranscript) {
      const transcriptContainerEl = this.lwc.refs.agentAssistTranscript;
      const transcriptEl = document.createElement("agent-assist-transcript");
      transcriptEl.setAttribute("namespace", this.lwc.recordId);
      transcriptContainerEl.appendChild(transcriptEl);
    }

    // Create Container UI Module element.
    const containerEl = document.createElement("agent-assist-ui-modules-v2");
    containerEl.generalConfig = { clipboardMode: "EVENT_ONLY" };
    containerEl.classList.add("agent-assist-ui-modules");
    const uiModulesWrapperEl = this.lwc.refs.agentAssistContainer;

    // Required attributes for UI Modules
    containerEl.setAttribute("use-configured-features", true);
    containerEl.setAttribute("namespace", this.lwc.recordId);

    // Optional attributes for UI Modules
    containerEl.setAttribute(
      "show-dark-mode-toggle",
      this.lwc.showDarkModeToggle
    );
    containerEl.setAttribute("show-header", this.lwc.showHeader);
    containerEl.setAttribute(
      "show-correctness-feedback",
      this.lwc.showCorrectnessFeedback
    );
    containerEl.setAttribute("disabled-features", this.lwc.disabledFeatures);

    // Create the UI Modules Connector.
    this.connector = new UiModulesConnector();
    const config = {
      // Basic config
      channel: this.lwc.channel,
      agentDesktop: "Custom",
      conversationProfileName: this.lwc.conversationProfile,

      // Connector options
      apiConfig: {
        authToken: this.lwc.token,
        customApiEndpoint: this.lwc.endpoint
      },
      eventBasedConfig: {
        notifierServerEndpoint: this.lwc.endpoint,
        library: "SocketIo"
      },

      // Salesforce specific config
      uiModuleEventOptions: {
        namespace: this.lwc.recordId
      },
      omitScriptNonce: true
    };

    // Initialize the UI Modules
    if (this.lwc.conversationName) {
      uiModulesWrapperEl.appendChild(containerEl);
      this.connector.init(config);
      if (this.lwc.debugMode) {
        this.lwc.debugLog("UiModulesConnector initialized with config:");
        console.log(config);
      }

      // Check if Dark Mode is (still) on from another UIM instance
      if (document.body.classList.contains("dark-mode")) {
        this.handleDarkModeToggled({ detail: { on: true } });
      }

      // Make the UI Modules visible
      uiModulesWrapperEl.classList.remove("hidden");
      if (this.lwc.showTranscript) {
        const transcriptContainerEl = this.lwc.refs.transcriptContainer;
        transcriptContainerEl.classList.remove("hidden");
      }
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // GENERATE CONVERSATION NAME OR FETCH ONE FROM UI CONNECTOR
  ////////////////////////////////////////////////////////////////////////////

  createRequestOptions(method, body = null) {
    // Construct fetch authed request options object
    const options = {
      method: method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `${this.lwc.token}`
      }
    };
    if (body) options.body = body;
    return options;
  }

  ////////////////////////////////////////////////////////////////////////////
  // HANDLE UI MODULE EVENTS
  ////////////////////////////////////////////////////////////////////////////

  initAgentAssistEvents() {
    this.lwc.debugLog("initAgentAssistEvents called");
    // Add event listeners for Agent Assist UI Modules events.
    if (this.lwc.channel === "chat") {
      this.lwc.debugLog("initAgentAssistEvents - this.lwc.channel is 'chat'");
      addAgentAssistEventListener(
        "api-connector-initialized",
        async () => await this.handleConnectorInitialized(),
        { namespace: this.lwc.recordId }
      );
    } else if (this.lwc.channel === "voice") {
      this.lwc.debugLog("initAgentAssistEvents - this.lwc.channel is 'voice'");
      addAgentAssistEventListener(
        "event-based-connector-initialized",
        async () => await this.handleConnectorInitialized(),
        { namespace: this.lwc.recordId }
      );
    }
    addAgentAssistEventListener(
      "copy-to-clipboard",
      (event) => this.handleCopyToClipboard(event),
      { namespace: this.lwc.recordId }
    );
    addAgentAssistEventListener(
      "dark-mode-toggled",
      (event) => this.handleDarkModeToggled(event),
      { namespace: this.lwc.recordId }
    );
  }

  async handleConnectorInitialized() {
    this.lwc.debugLog("handleConnectorInitialized called");

    // Ensure we have a token before proceeding.
    while (!this.lwc.token) {
      this.lwc.debugLog("waiting for ui connector token...");
      await new Promise((resolve) =>
        setTimeout(resolve, TOKEN_WAIT_INTERVAL_MS)
      );
    }
    this.lwc.debugLog(`ui connector token: ${this.lwc.token}`);

    // Poll until Dialogflow confirms the existence of the conversationName.
    if (this.lwc.channel !== "chat") {
      await this.pollDialogflowForConversationExistence();
    }

    // Set the active conversation for UIM on connector initialization.
    dispatchAgentAssistEvent(
      "active-conversation-selected",
      { detail: { conversationName: this.lwc.conversationName } },
      { namespace: this.lwc.recordId }
    );
  }

  async pollDialogflowForConversationExistence(
    maxRetries = POLL_MAX_RETRIES,
    initialDelay = POLL_INITIAL_DELAY_MS
  ) {
    // Poll for this.conversationName until Dialogflow confirms it exists.
    let delayMs = initialDelay;
    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await fetch(
          `${this.lwc.endpoint}/${DIALOGFLOW_API_VERSION}/${this.lwc.conversationName}`,
          this.createRequestOptions("GET")
        );
        this.lwc.debugLog(
          `pollDialogflowForConversationExistence: ${response.status}...`
        );
        if (response.ok) return true; // Conversation exists, exit polling
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        delayMs += POLL_DELAY_INCREMENT_MS;
      } catch (error) {
        this.lwc.debugLog(
          `pollDialogflowForConversationExistence - error: ${error}`
        );
      }
    }
    this.lwc.debugLog(
      `pollDialogflowForConversationExistence - failed ${maxRetries} times`
    );
    return false;
  }

  async deleteConversationName(conversationIntegrationKey) {
    // Deletes conversationIntegrationKey:conversationName pair from Redis.
    return await fetch(
      this.lwc.endpoint +
        "/conversation-name?conversationIntegrationKey=" +
        conversationIntegrationKey,
      this.createRequestOptions("DELETE")
    )
      .then((res) => this.lwc.debugLog(`deleteConversationName: ${res.status}`))
      .catch((err) => console.error(err));
  }

  async fetchConversationLifecycleState() {
    return await fetch(
      `${this.lwc.endpoint}/${DIALOGFLOW_API_VERSION}/${this.lwc.conversationName}`,
      this.createRequestOptions("GET")
    )
      .then((res) => res.json())
      .then((conversation) => conversation.lifecycleState);
  }

  async handleCopyToClipboard(event) {
    // Handle copy to clipboard event from UI Modules.
    navigator.clipboard.writeText(event.detail.textToCopy);
  }

  handleDarkModeToggled(event) {
    // Toggle dark mode for the transcript container.
    if (event.detail.on) {
      this.lwc.refs.transcriptContainer.classList.add("dark-mode");
    } else {
      this.lwc.refs.transcriptContainer.classList.remove("dark-mode");
    }
  }

  async isConversationCompleted(conversationIntegrationKey) {
    // Checks if this.conversationName is COMPLETED.
    const lifecycleState = await this.fetchConversationLifecycleState();
    if (lifecycleState === "COMPLETED") {
      this.lwc.debugLog(`conversation COMPLETED, deleting key from redis.`);
      this.deleteConversationName(conversationIntegrationKey);
      return true;
    }
    return false;
  }

  ////////////////////////////////////////////////////////////////////////////
  // DEBUG & DEMO
  ////////////////////////////////////////////////////////////////////////////

  initEventDragnet() {
    // A debug utility to listen for and log every Agent Assist event type.
    this.lwc.debugLog(
      `InitEventDragnet - listening for ${agentAssistEventNames.length} event types...`
    );
    agentAssistEventNames.forEach((eventName) => {
      // this.lwc.debugLog(`initEventDragnet - listening for ${eventName}`);
      try {
        addAgentAssistEventListener(
          eventName,
          (event) => {
            this.lwc.debugLog(`initEventDragnet - heard: ${event.type}`);
            if (event.detail) {
              console.log(event.detail);
            }
          },
          { namespace: this.lwc.recordId }
        );
      } catch (error) {
        console.error(error);
      }
    });
  }
}
