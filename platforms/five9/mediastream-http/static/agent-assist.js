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

class AgentAssist {
  constructor() {
    this.uiConnectorUrl = window.uiConnectorUrl;
    this.conversationProfile = window.conversationProfile;
    this.features = window.features;
    this.channel = "voice";
    this.platform = "five9";

    // Check that required config values are present.
    if (!this.uiConnectorUrl) {
      console.error("[Agent Assist] this.uiConnectorUrl is not set.")
    }
    if (!this.conversationProfile) {
      console.error("[Agent Assist] this.conversationProfile is not set.")
    }

    this.callId = this.getCallId();

    this.authToken = window.authToken || "";
    this.conversationName = null;
    this.connector = null;
    this.containerEl = null;
  }

  async init() {
    this.initAgentAssistEventListeners();

    const connector = new UiModulesConnector();
    const config = {
      channel: "voice",
      features: this.features,
      agentDesktop: "Custom",
      conversationProfileName: this.conversationProfile,
      apiConfig: {
        authToken: this.authToken,
        customApiEndpoint: this.uiConnectorUrl,
      },
      eventBasedConfig: {
        notifierServerEndpoint: this.uiConnectorUrl,
        library: "SocketIo",
      }
    };

    this.containerEl = document.createElement("agent-assist-ui-modules-v2");
    this.containerEl.classList.add("agent-assist-ui-modules");
    this.containerEl.setAttribute("features", this.features);

    console.debug("createTranscript");
    const transcriptContainer = document.querySelector(".transcript-container");
    const transcriptEl = document.createElement("agent-assist-transcript");
    transcriptContainer.appendChild(transcriptEl);

    const uiModulesWrapperEl = document.querySelector(".ui-modules-container");
    uiModulesWrapperEl.appendChild(this.containerEl);

    this.connector = connector;
    connector.init(config);

    this.initDarkMode();
  }

  getCallId() {
    let callId = "";
    const params = new URLSearchParams(window.location.search);
    callId = params.get("call_id") || "";
    return callId;
  }

  generateConversationName() {
    // Format: <platform>-<10 digit zero-padded call_id>
    const formattedCallId = String(this.callId).padStart(10, "0");
    const conversationId = `${this.platform}-${formattedCallId}`;

    let projectId = "YOUR_PROJECT_ID";
    let location = "global";
    const conversationProfile = this.conversationProfile;
    const match = conversationProfile.match(
      /projects\/([\w-]+)\/locations\/([\w-]+)/,
    );
    if (match) {
      if (match[1]) projectId = match[1];
      if (match[2]) location = match[2];
    }
    const name = `projects/${projectId}/locations/${location}/conversations/${conversationId}`;
    this.conversationName = name;
  }

  initAgentAssistEventListeners() {
    console.debug("initAgentAssistEventListeners");
    this.generateConversationName();

    addAgentAssistEventListener(
      "api-connector-initialized",
      (event) => {
        dispatchAgentAssistEvent(
          "active-conversation-selected",
          { detail: { conversationName: this.conversationName } }
        );
      }
    );

    addAgentAssistEventListener(
      "dark-mode-toggled",
      (event) => window.localStorage.setItem("agentAssistDarkMode", event.detail.on)
    );
  }

  initDarkMode() {
    let darkMode =
      window.localStorage.getItem("agentAssistDarkMode") === "true" ||
      document.body.classList.contains("dark-mode");
    window.localStorage.setItem("agentAssistDarkMode", darkMode);
    if (darkMode && !document.body.classList.contains("dark-mode")) {
      dispatchAgentAssistEvent(
        "dark-mode-toggled",
        { detail: { on: true } }
      );
    }
  }
}

window.addEventListener("load", async () => {
  window.agentAssist = new AgentAssist();
  await window.agentAssist.init();
});
