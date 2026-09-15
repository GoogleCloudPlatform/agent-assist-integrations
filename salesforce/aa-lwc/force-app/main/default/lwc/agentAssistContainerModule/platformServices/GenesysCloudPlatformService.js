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

import BasePlatformService from "./BasePlatformService";
import getLatestInteractionId from "@salesforce/apex/AgentAssistAuthController.getLatestInteractionId";

// Module-level shared cache across LWC instances on different record tabs/subtabs
let latestActiveConversationId = null;



const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isValidId(str) {
  if (typeof str !== "string") return false;
  return UUID_REGEX.test(str.trim());
}

function findUuidInObject(obj, depth = 0) {
  if (!obj || depth > 5) return null;
  if (typeof obj === "string" && isValidId(obj)) return obj.trim();
  if (typeof obj !== "object") return null;

  const priorityKeys = [
    "conversationId",
    "interactionId",
    "id",
    "conversationIntegrationKey",
    "call.conversationid",
    "currentInteractionId"
  ];
  for (const key of priorityKeys) {
    if (obj[key] && isValidId(obj[key])) return obj[key].trim();
  }

  if (Array.isArray(obj)) {
    for (const item of obj) {
      const found = findUuidInObject(item, depth + 1);
      if (found) return found;
    }
    return null;
  }

  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === "object") {
      const found = findUuidInObject(v, depth + 1);
      if (found) return found;
    } else if (
      typeof v === "string" &&
      isValidId(v) &&
      (k.toLowerCase().includes("id") ||
        k.toLowerCase().includes("conversation") ||
        k.toLowerCase().includes("interaction"))
    ) {
      return v.trim();
    }
  }
  return null;
}

function getCachedConversationId() {
  if (latestActiveConversationId && isValidId(latestActiveConversationId)) {
    return latestActiveConversationId;
  }
  try {
    const keys = [
      "purecloud_current_conversation_id",
      "genesys_current_conversation_id"
    ];
    for (const key of keys) {
      const local = window.localStorage?.getItem(key);
      if (local) {
        if (isValidId(local)) return local.trim();
        window.localStorage.removeItem(key);
      }
      const session = window.sessionStorage?.getItem(key);
      if (session) {
        if (isValidId(session)) return session.trim();
        window.sessionStorage.removeItem(key);
      }
    }
  } catch (e) {}
  return null;
}

function setCachedConversationId(id) {
  if (!id || !isValidId(id)) return;
  latestActiveConversationId = id.trim();
  try {
    window.localStorage?.setItem(
      "purecloud_current_conversation_id",
      latestActiveConversationId
    );
    window.sessionStorage?.setItem(
      "purecloud_current_conversation_id",
      latestActiveConversationId
    );
  } catch (e) {}
}

export default class GenesysCloudPlatformService extends BasePlatformService {
  pollingTimeout = null;
  isTeardown = false;
  genesysConversationId = null;

  constructor(lwc, refs) {
    super(lwc, refs);
    this.handleConversationEndedForGenesysCloud =
      this.handleConversationEndedForGenesysCloud.bind(this);
    this.handleGenesysMessage = this.handleGenesysMessage.bind(this);
  }

  async init() {
    if (this.isTeardown) return;
    this.lwc.debugLog("initGenesysCloud called");
    try {
      window.addEventListener("message", this.handleGenesysMessage);
    } catch (e) {}
    // Query Salesforce Task associated with this record or recent CTI calls first
    if (!this.genesysConversationId) {
      try {
        const apexInteractionId = await getLatestInteractionId({
          recordId: this.lwc.recordId
        });
        if (apexInteractionId && isValidId(apexInteractionId)) {
          this.genesysConversationId = apexInteractionId.trim();
          setCachedConversationId(this.genesysConversationId);
          this.lwc.debugLog(
            `Found active Genesys conversation ID from Salesforce Task: ${this.genesysConversationId}`
          );
        }
      } catch (e) {}
    }
    if (!this.genesysConversationId) {
      const cachedId = getCachedConversationId();
      if (cachedId) {
        this.genesysConversationId = cachedId;
        this.lwc.debugLog(`Using cached Genesys conversation ID: ${cachedId}`);
      }
    }
    if (!this.genesysConversationId) {
      this.lwc.debugLog(
        "Waiting for Genesys conversation ID from CTI event or Task..."
      );
      await this.waitForGenesysConversationId();
    }
    if (this.isTeardown || !this.genesysConversationId) return;

    const conversationName = await this.fetchConversationName(
      this.genesysConversationId
    );
    if (this.isTeardown) return;
    this.lwc.conversationName = conversationName;

    if (
      !this.lwc.conversationName ||
      (await this.isConversationCompleted(this.genesysConversationId))
    ) {
      if (this.isTeardown) return;
      this.pollForConversationNameByIntegrationKey(this.genesysConversationId);
    }
    if (this.isTeardown) return;
    this.listenToAgentAssistEventsForGenesysCloud();
  }

  requestGenesysInteractions() {
    const rawMessages = [
      { type: "purecloud.subscribe", data: { category: "interaction" } },
      { type: "purecloud.subscribe", data: { category: "notification" } },
      { type: "purecloud.getInteractions" },
      { category: "purecloud.getInteractions" },
      { action: "getInteractions" }
    ];
    const targets = new Set();
    try {
      if (window) targets.add(window);
    } catch (e) {}
    try {
      if (window.parent && window.parent !== window) targets.add(window.parent);
    } catch (e) {}
    try {
      if (window.top && window.top !== window) targets.add(window.top);
    } catch (e) {}
    const collectIframes = (root) => {
      try {
        const iframes = root.querySelectorAll
          ? Array.from(root.querySelectorAll("iframe"))
          : [];
        root.querySelectorAll("*").forEach((el) => {
          if (el.shadowRoot) iframes.push(...collectIframes(el.shadowRoot));
        });
        return iframes;
      } catch (e) {
        return [];
      }
    };
    try {
      collectIframes(document).forEach((iframe) => {
        if (iframe.contentWindow) targets.add(iframe.contentWindow);
      });
    } catch (e) {}
    targets.forEach((targetWindow) => {
      rawMessages.forEach((msgObj) => {
        try {
          targetWindow.postMessage(msgObj, "*");
          targetWindow.postMessage(JSON.stringify(msgObj), "*");
        } catch (e) {}
      });
    });
  }

  extractConversationId(payload) {
    if (!payload) return null;
    return findUuidInObject(payload);
  }

  handleGenesysMessage(event) {
    const trustedOriginPattern = /^https:\/\/apps\.(?:[a-z0-9-]+\.pure\.cloud|mypurecloud\.(?:com|ie|de|jp|com\.au))$/i;
    if (!trustedOriginPattern.test(event.origin)) {
      return;
    }
    try {
      let payload = event.data;
      if (
        typeof payload === "string" &&
        (payload.startsWith("{") || payload.startsWith("["))
      ) {
        try {
          payload = JSON.parse(payload);
        } catch (e) {}
      }
      if (
        !payload ||
        (typeof payload !== "object" && typeof payload !== "string")
      )
        return;

      const extractedId = this.extractConversationId(payload);
      if (extractedId) {
        this.lwc.debugLog(
          `Extracted Genesys conversation ID from message: ${extractedId}`
        );
        setCachedConversationId(extractedId);
        if (this.genesysConversationId !== extractedId) {
          this.genesysConversationId = extractedId;
          this.lwc.debugLog(
            `Set active Genesys conversation ID: ${extractedId}`
          );
          if (this.pollingTimeout) {
            clearTimeout(this.pollingTimeout);
          }
          this.pollForConversationNameByIntegrationKey(extractedId);
        }
      }
    } catch (e) {}
  }

  async waitForGenesysConversationId() {
    let checkCount = 0;
    return new Promise((resolve) => {
      const interval = setInterval(async () => {
        if (this.genesysConversationId || this.isTeardown) {
          clearInterval(interval);
          resolve();
          return;
        }

        checkCount++;
        // Check if another tab/service updated the cache
        const cachedId = getCachedConversationId();
        if (cachedId) {
          this.genesysConversationId = cachedId;
          this.lwc.debugLog(
            `Discovered cached Genesys conversation ID during wait: ${cachedId}`
          );
          clearInterval(interval);
          resolve();
          return;
        }

        // Periodically check Salesforce Task via Apex
        if (checkCount % 2 === 0) {
          try {
            const apexId = await getLatestInteractionId({
              recordId: this.lwc.recordId
            });
            if (apexId && isValidId(apexId)) {
              this.genesysConversationId = apexId.trim();
              setCachedConversationId(this.genesysConversationId);
              this.lwc.debugLog(
                `Discovered Genesys conversation ID from Task during wait: ${this.genesysConversationId}`
              );
              clearInterval(interval);
              resolve();
              return;
            }
          } catch (e) {}
        }

        if (checkCount % 3 === 0) {
          this.lwc.debugLog(
            `Waiting for CTI conversation ID... (storage/cookies/task check #${checkCount})`
          );
        }

        // Proactively ping Genesys CTI softphone iframe
        this.requestGenesysInteractions();
      }, 1000);
    });
  }

  teardown() {
    this.isTeardown = true;
    super.teardown();
    if (this.pollingTimeout) {
      clearTimeout(this.pollingTimeout);
    }
    try {
      window.removeEventListener("message", this.handleGenesysMessage);
    } catch (e) {}
  }

  listenToAgentAssistEventsForGenesysCloud() {
    this.lwc.debugLog("listenToAgentAssistEventsForGenesysCloud called");
    addAgentAssistEventListener(
      "conversation-completed",
      this.handleConversationEndedForGenesysCloud,
      { namespace: this.lwc.recordId }
    );
  }

  async fetchConversationName(conversationIntegrationKey, timeout = 5000) {
    if (!conversationIntegrationKey) {
      this.lwc.debugLog(
        "fetchConversationName called with empty integration key"
      );
      return null;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const url = `${this.lwc.endpoint}/conversation-name?conversationIntegrationKey=${encodeURIComponent(conversationIntegrationKey)}`;
      this.lwc.debugLog(
        `[AgentAssist] Querying UI Connector for conversationName: ${url}`
      );
      const response = await fetch(url, {
        ...this.createRequestOptions("GET"),
        signal: controller.signal
      });

      if (response?.ok) {
        const data = await response.json();
        this.lwc.debugLog(
          `[AgentAssist] UI Connector response: ${JSON.stringify(data)}`
        );
        return data.conversationName;
      } else if (response && response.status !== 404) {
        this.lwc.debugLog(
          `[AgentAssist] Error fetching conversation name: ${response.status} ${response.statusText}`
        );
      } else {
        this.lwc.debugLog(
          `[AgentAssist] UI Connector: No active conversation mapped yet (HTTP ${response?.status}).`
        );
      }
    } catch (error) {
      if (error.name === "AbortError") {
        throw error;
      }
      this.lwc.debugLog(
        `[AgentAssist] Network error fetching conversation name: ${error.message}`
      );
    } finally {
      clearTimeout(timeoutId);
    }
    return null;
  }

  async pollForConversationNameByIntegrationKey(
    conversationIntegrationKey,
    { initialDelay = 1000, maxDelay = 10000, requestTimeoutMs = 9900 } = {}
  ) {
    if (this.pollingTimeout) {
      clearTimeout(this.pollingTimeout);
    }
    if (!conversationIntegrationKey) {
      this.lwc.debugLog(
        "pollForConversationNameByIntegrationKey called with empty integration key"
      );
      return;
    }

    this.lwc.conversationName = undefined;
    let attempt = 0;

    const poll = async (delayMs) => {
      if (this.isTeardown) return;
      attempt++;

      // 1. Check if a newer active interaction ID was recorded in cache or another tab
      try {
        const latestStorageId = getCachedConversationId();
        if (
          latestStorageId &&
          latestStorageId !== conversationIntegrationKey &&
          isValidId(latestStorageId)
        ) {
          this.lwc.debugLog(
            `[AgentAssist] Switching polling to newer interaction ID: ${latestStorageId}`
          );
          this.genesysConversationId = latestStorageId;
          this.pollForConversationNameByIntegrationKey(latestStorageId);
          return;
        }

        // 2. Periodically query Salesforce Task via Apex for newly popped interactions
        if (attempt % 2 === 0) {
          const apexId = await getLatestInteractionId({
            recordId: this.lwc.recordId
          });
          if (
            apexId &&
            isValidId(apexId) &&
            apexId.trim() !== conversationIntegrationKey
          ) {
            this.lwc.debugLog(
              `[AgentAssist] Discovered new interaction ID from Salesforce Task: ${apexId.trim()}`
            );
            this.genesysConversationId = apexId.trim();
            setCachedConversationId(this.genesysConversationId);
            this.pollForConversationNameByIntegrationKey(
              this.genesysConversationId
            );
            return;
          }
        }
      } catch (e) {}

      this.lwc.debugLog(
        `Polling for conversationName... (attempt ${attempt}, delay: ${delayMs}ms)`
      );

      try {
        const conversationName = await this.fetchConversationName(
          conversationIntegrationKey,
          requestTimeoutMs
        );
        if (this.isTeardown) return;

        if (conversationName) {
          if (this.isTeardown) return;
          this.lwc.conversationName = conversationName;
          this.lwc.debugLog(
            `Found conversationName: ${this.lwc.conversationName}. Initializing UI Modules.`
          );
          this.handleConnectorInitialized();
          this.initUIModules();
          return;
        } else {
          // If conversation completed or empty after multiple attempts, purge stale cache
          if (
            attempt >= 4 &&
            latestActiveConversationId === conversationIntegrationKey
          ) {
            this.lwc.debugLog(
              `[AgentAssist] Stale conversation ID ${conversationIntegrationKey} returned empty conversationName. Purging cache.`
            );
            latestActiveConversationId = null;
            try {
              window.localStorage.removeItem(
                "purecloud_current_conversation_id"
              );
              window.sessionStorage.removeItem(
                "purecloud_current_conversation_id"
              );
            } catch (e) {}
          }
          throw new Error("Conversation not found or already completed.");
        }
      } catch (error) {
        if (this.isTeardown) return;
        this.lwc.debugLog(
          `Polling attempt ${attempt} failed: ${error.message}`
        );

        const increment = (maxDelay - initialDelay) / 10;
        const nextDelay = Math.min(maxDelay, delayMs + increment);

        this.pollingTimeout = setTimeout(() => poll(nextDelay), delayMs);
      }
    };

    poll(initialDelay);
  }

  handleConversationEndedForGenesysCloud() {
    if (this.isTeardown) return;
    this.lwc.debugLog("handleConversationEndedForGenesysCloud called");
    if (
      this.lwc.features &&
      this.lwc.features.includes("CONVERSATION_SUMMARIZATION")
    ) {
      this.lwc.triggerSummarization();
    }
    if (this.genesysConversationId) {
      this.pollForConversationNameByIntegrationKey(this.genesysConversationId);
    }
  }
}
