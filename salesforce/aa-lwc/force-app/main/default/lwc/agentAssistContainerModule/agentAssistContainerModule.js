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

import { api, wire } from "lwc";
import { loadScript, loadStyle } from "lightning/platformResourceLoader";
import { getRecord, getFieldValue } from "lightning/uiRecordApi";
import { MessageContext } from "lightning/messageService";

// static resources
import ui_modules from "@salesforce/resourceUrl/ui_modules";
import global_styles from "@salesforce/resourceUrl/global_styles";
import google_logo from "@salesforce/resourceUrl/google_logo";

import { LightningElement } from "lwc";
import agentAssistEventNames from "./data/agentAssistEventNames";
import sampleContext from "./data/sampleContext";
import {
  DIALOGFLOW_API_VERSION,
  TOKEN_REFRESH_CHECK_INTERVAL_MS,
  CONTEXT_INJECTION_DELAY_MS
} from "./config";

// Platform Services
import MessagingPlatformService from "./platformServices/MessagingPlatformService";
import TwilioFlexPlatformService from "./platformServices/TwilioFlexPlatformService";
import ServiceCloudVoicePlatformService from "./platformServices/ServiceCloudVoicePlatformService";

// This Zone.js flag must be set to prevent monkey-patching of DOM APIs,
// some of which are forbidden by Lightning Web Security (LWS).
// For more details see https://developer.salesforce.com/docs/component-library/tools/lws-distortion-viewer.
window.__Zone_disable_on_property = true;
// Generally useful flags for UIM debugging and environment configuration.
// window._uiModuleFlags = { debug: true };

export default class AgentAssistContainerModule extends LightningElement {
  // LWC Static Config - set these in Lightning App Builder:
  // Drag and drop agentAssistContainerModule onto page, select, and fill inputs
  @api debugMode; // e.g. false
  @api endpoint; // e.g. https://your-ui-connector-endpoint.a.run.app
  @api conversationProfile; // e.g. projects/your-gcp-project-id/locations/your-location/conversationProfiles/your-conversation-profile-id
  @api channel; // Either 'chat' or 'voice'
  @api platform; // One of 'messaging', 'twilioflex', 'servicecloudvoice-nice'
  @api consumerKey; // SF Connected App Consumer Key
  @api consumerSecret; // SF Connected App Consumer Secret
  @api containerHeight;
  // UI Module optional attributes
  @api showDarkModeToggle = false;
  @api showHeader = false;
  @api showCorrectnessFeedback = false;
  @api disabledFeatures = "";

  // LWC Public Properties - set at runtime by platform services
  // @api decorator allows external read and write
  @api loadError = null;
  @api conversationId = null;
  @api conversationName = null;
  @api cancelSummarizationTimeout = null;
  @api token = null;
  @api showTranscript = false;

  // LWC Private Properties
  _heightApplied = false;

  // LWC Wired Properties
  // https://developer.salesforce.com/docs/platform/lwc/guide/data-wire-service-about.html
  @api recordId;
  @wire(MessageContext) messageContext;
  @wire(getRecord, { recordId: "$recordId", fields: ["Contact.Phone"] })
  contact;
  @wire(getRecord, {
    recordId: "$recordId",
    fields: ["VoiceCall.VendorCallKey"]
  })
  voiceCall;

  // LWC Getters - deconstruct values from @wire objects on demand
  @api get contactPhone() {
    return getFieldValue(this.contact.data, "Contact.Phone");
  }
  @api get vendorCallKey() {
    return getFieldValue(this.voiceCall.data, "VoiceCall.VendorCallKey");
  }
  @api get projectLocationName() {
    return this.conversationProfile.split("/conversationProfiles")[0];
  }

  googleLogoUrl = google_logo;
  @api platformService = null;
  conversationNamePollingInterval = null;
  tokenRefreshInterval = null;

  @api
  connectedCallback() {
    this.debugLog("connectedCallback called");
    this.showTranscript = this.channel === "voice" || this.debugMode;
    this.inspectConfig();
    // Defer height application to renderedCallback so the template is available
  }

  async renderedCallback() {
    this.debugLog("renderedCallback called");

    // Apply height override once the template has rendered
    if (this.containerHeight && !this._heightApplied) {
      this.applyHeightOverride();
      this._heightApplied = true;
    }

    if (!this.platformService) {
      // Pass necessary refs to the service in an LWS-compliant way.
      // This must be done at instantiation time before init() is called.
      const refs = {
        conversationToolkitApi: this.refs.conversationToolkitApi,
        serviceCloudVoiceToolkitApi: this.refs.serviceCloudVoiceToolkitApi
      };

      // Instantiate the correct platform service
      if (this.platform === "messaging") {
        this.platformService = new MessagingPlatformService(this, refs);
      } else if (this.platform === "twilioflex") {
        this.platformService = new TwilioFlexPlatformService(this, refs);
      } else if (this.platform.includes("servicecloudvoice")) {
        this.platformService = new ServiceCloudVoicePlatformService(this, refs);
      } else {
        this.loadError = new Error(`Unsupported platform: ${this.platform}`);
        this.debugLog(this.loadError.message);
      }
    }

    if (this.platformService && !this.platformService.initialized) {
      this.platformService.initialized = true; // Prevent re-initialization

      // Get a UI Connector auth token
      this.token = await this.platformService.registerAuthToken();

      // Automatically check and refresh the token dynamically
      this.tokenRefreshInterval = setInterval(async () => {
        await this.platformService.checkAndRefreshToken();
      }, TOKEN_REFRESH_CHECK_INTERVAL_MS);
      // Run an initial check immediately
      await this.platformService.checkAndRefreshToken();

      // Load static resources. Order matters, due to LWS & Lightning Locker.
      this.debugLog("UI Modules javascript and css loading...");
      await loadScript(this, ui_modules + "/transcript.js");
      await loadScript(this, ui_modules + "/container.js");
      await loadScript(this, ui_modules + "/common.js");
      await loadStyle(this, global_styles);
      this.debugLog("UI Modules javascript and css loaded.");

      // Optionally, Log Agent Assist events
      if (this.debugMode) this.platformService.initEventDragnet();

      // Initialize Agent Assist UI Modules
      this.platformService.initAgentAssistEvents();

      // Initialize platform-specific logic
      await this.platformService.init();

      // Wait for a conversationName before initializing UI Modules
      if (!this.conversationName) {
        await this.waitForConversationName();
      } else {
        this.platformService.initUIModules();
      }

      // For demo and testing purposes - read more:
      // https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.locations.conversations/ingestContextReferences
      // this.ingestDemoContextReferences();
    }
  }

  disconnectedCallback() {
    this.debugLog("disconnectedCallback called");

    if (this.platformService) {
      this.platformService.teardown();
    }
    if (this.conversationNamePollingInterval) {
      clearInterval(this.conversationNamePollingInterval);
    }
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval);
    }

    // Clears all listeners (_uiModuleEventTarget is not attached to the DOM)
    if (window._uiModuleEventTarget) {
      window._uiModuleEventTarget = window._uiModuleEventTarget.cloneNode(true);
    }
  }

  async waitForConversationName() {
    this.debugLog(`waiting for a conversationName to init UI Modules...`);
    return new Promise((resolve) => {
      this.conversationNamePollingInterval = setInterval(() => {
        if (this.conversationName) {
          clearInterval(this.conversationNamePollingInterval);
          this.conversationNamePollingInterval = null;
          this.debugLog(`this.conversationId: ${this.conversationId}`);
          this.debugLog(`this.conversationName: ${this.conversationName}`);
          if (this.platformService) {
            this.platformService.initUIModules();
          }
          resolve();
        }
      }, 1000);
    });
  }

  @api
  triggerSummarization() {
    // The UI modules container is a child component, so we must query for it first.
    const uiModulesElement = this.template.querySelector(
      "agent-assist-ui-modules-v2"
    );
    if (uiModulesElement) {
      // Now query for the button within the UI modules container.
      const summarizationButton = uiModulesElement.querySelector(
        '[data-test-id="generate-summary-button"]'
      );
      if (
        summarizationButton &&
        !summarizationButton.hasAttribute("disabled") &&
        !summarizationButton.disabled
      ) {
        summarizationButton.dispatchEvent(new Event("click"));
        this.debugLog(
          "Summarization triggered by clicking the generate summary button."
        );
      }
    }
  }

  applyHeightOverride() {
    if (!this.containerHeight || isNaN(parseInt(this.containerHeight, 10))) {
      this.debugLog(`Invalid containerHeight value: ${this.containerHeight}`);
      return;
    }
    this.template.host.style.setProperty(
      "--aa-container-height",
      this.containerHeight
    );
  }

  @api
  debugLog(message) {
    // A debug utility to log messages only if debugMode is set to true.
    if (this.debugMode) {
      console.log(
        `%c[AgentAssist]%c ${message}`,
        "background-color: #0070d2; color: #ffffff; padding: 2px 4px; border-radius: 3px; font-weight: bold;",
        ""
      );
    }
  }

  @api
  inspectConfig() {
    // A debug utility to check the runtime config of the Agent Assist LWC.
    this.debugLog(`this.endpoint - ${this.endpoint}`);
    this.debugLog(`this.showTranscript - ${this.showTranscript}`);
    this.debugLog(`this.conversationProfile - ${this.conversationProfile}`);
    this.debugLog(`this.channel - ${this.channel}`);
    this.debugLog(`this.platform - ${this.platform}`);
    this.debugLog(`this.consumerKey - ${this.consumerKey}`);
    this.debugLog(`this.consumerSecret - ${this.consumerSecret}`);
  }

  @api
  ingestDemoContextReferences() {
    // Injects context into the Dialogflow conversation for demos and testing.
    // https://cloud.google.com/dialogflow/es/docs/reference/rest/v2/projects.locations.conversations/ingestContextReferences
    const injectContext = () => {
      let url = `${this.endpoint}/${DIALOGFLOW_API_VERSION}/${this.conversationName}:ingestContextReferences`;
      let body = JSON.stringify({
        contextReferences: {
          context: {
            contextContents: [
              { content: sampleContext, contentFormat: "JSON" }
            ],
            languageCode: "en-us",
            updateMode: "OVERWRITE"
          }
        }
      });
      fetch(url, this.platformService.createRequestOptions("POST", body))
        .then((res) => res.text())
        .then((data) => {
          this.debugLog("ingestDemoContextReferences ran successfully");
          console.log(JSON.parse(data));
        })
        .catch((err) => {
          this.debugLog(`ingestDemoContextReferences failed: ${err.message}`);
        });
    };
    setTimeout(injectContext, CONTEXT_INJECTION_DELAY_MS);
  }
}
