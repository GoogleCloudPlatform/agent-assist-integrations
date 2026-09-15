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

import GenesysCloudPlatformService from "../GenesysCloudPlatformService";
import {
  setupPlatformServiceTest,
  createMockLwcComponent,
  createMockRefs
} from "../testUtils";

describe("GenesysCloudPlatformService", () => {
  let mockLwc;
  let mockRefs;
  let genesysCloudPlatformService;

  setupPlatformServiceTest();

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();

    // Create mock LWC component
    mockLwc = createMockLwcComponent({ platform: "genesyscloud" });

    // Create mock refs
    mockRefs = createMockRefs();

    // Create instance of GenesysCloudPlatformService
    genesysCloudPlatformService = new GenesysCloudPlatformService(
      mockLwc,
      mockRefs
    );
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe("constructor", () => {
    it("initializes with lwc and refs parameters", () => {
      expect(genesysCloudPlatformService.lwc).toBe(mockLwc);
      expect(genesysCloudPlatformService.refs).toBe(mockRefs);
      expect(
        genesysCloudPlatformService.handleConversationEndedForGenesysCloud
      ).toBeDefined();
    });
  });

  describe("init", () => {
    it("executes without errors", () => {
      expect(() => {
        genesysCloudPlatformService.init();
      }).not.toThrow();
    });

    it("logs initGenesysCloud call", () => {
      genesysCloudPlatformService.init();
      expect(mockLwc.debugLog).toHaveBeenCalledWith("initGenesysCloud called");
    });

    it("fetches conversation name when conversationName is not set", async () => {
      genesysCloudPlatformService.genesysConversationId = "test-genesys-id";
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ conversationName: "test-conversation-name" })
      });

      await genesysCloudPlatformService.init();

      expect(global.fetch).toHaveBeenCalledWith(
        "https://test-endpoint.com/conversation-name?conversationIntegrationKey=test-genesys-id",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: "test-token"
          },
          signal: expect.any(AbortSignal)
        }
      );
    });

    it("polls for conversation name when conversationName is not set and not completed", async () => {
      genesysCloudPlatformService.genesysConversationId = "test-genesys-id";
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ conversationName: null })
      });

      const spy = jest.spyOn(
        genesysCloudPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      await genesysCloudPlatformService.init();

      expect(spy).toHaveBeenCalledWith("test-genesys-id");
    });

    it("aborts early if isTeardown is true", async () => {
      genesysCloudPlatformService.isTeardown = true;
      const fetchSpy = jest.spyOn(
        genesysCloudPlatformService,
        "fetchConversationName"
      );

      await genesysCloudPlatformService.init();

      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  describe("waitForGenesysConversationId", () => {
    it("resolves when genesysConversationId becomes available", async () => {
      jest.useFakeTimers();
      genesysCloudPlatformService.genesysConversationId = null;
      let resolved = false;

      const promise = genesysCloudPlatformService
        .waitForGenesysConversationId()
        .then(() => {
          resolved = true;
        });

      expect(resolved).toBe(false);

      jest.advanceTimersByTime(1000);
      expect(resolved).toBe(false);

      // Set genesys ID
      genesysCloudPlatformService.genesysConversationId = "abcd-1234";

      jest.advanceTimersByTime(1000);
      await promise;

      expect(resolved).toBe(true);
    });

    it("resolves when isTeardown is true", async () => {
      jest.useFakeTimers();
      genesysCloudPlatformService.genesysConversationId = null;
      let resolved = false;

      const promise = genesysCloudPlatformService
        .waitForGenesysConversationId()
        .then(() => {
          resolved = true;
        });

      expect(resolved).toBe(false);

      genesysCloudPlatformService.isTeardown = true;

      jest.advanceTimersByTime(1000);
      await promise;

      expect(resolved).toBe(true);
    });
  });

  describe("handleGenesysMessage", () => {
    it("sets genesysConversationId and starts polling on interactionSubscription", () => {
      const spy = jest.spyOn(
        genesysCloudPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      const event = {
        origin: "https://apps.usw2.pure.cloud",
        data: {
          type: "interactionSubscription",
          data: {
            interaction: {
              id: "11111111-2222-3333-4444-555555555555"
            }
          }
        }
      };

      genesysCloudPlatformService.handleGenesysMessage(event);

      expect(genesysCloudPlatformService.genesysConversationId).toBe(
        "11111111-2222-3333-4444-555555555555"
      );
      expect(spy).toHaveBeenCalledWith("11111111-2222-3333-4444-555555555555");
    });

    it("clears old polling timeout and starts new polling if already polling", () => {
      const spy = jest.spyOn(
        genesysCloudPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");
      genesysCloudPlatformService.pollingTimeout = "existing-timeout";

      const event = {
        origin: "https://apps.mypurecloud.com",
        data: JSON.stringify({
          type: "PureCloud.Interaction",
          data: {
            id: "66666666-7777-8888-9999-000000000000"
          }
        })
      };

      genesysCloudPlatformService.handleGenesysMessage(event);

      expect(genesysCloudPlatformService.genesysConversationId).toBe(
        "66666666-7777-8888-9999-000000000000"
      );
      expect(clearTimeoutSpy).toHaveBeenCalledWith("existing-timeout");
      expect(spy).toHaveBeenCalledWith("66666666-7777-8888-9999-000000000000");
    });
  });

  describe("teardown", () => {
    it("executes without errors", () => {
      expect(() => {
        genesysCloudPlatformService.teardown();
      }).not.toThrow();
    });

    it("clears polling timeout", () => {
      genesysCloudPlatformService.pollingTimeout = "some-timeout";
      const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");

      genesysCloudPlatformService.teardown();

      expect(clearTimeoutSpy).toHaveBeenCalledWith("some-timeout");
    });
  });

  describe("listenToAgentAssistEventsForGenesysCloud", () => {
    it("adds event listener for conversation-completed", () => {
      genesysCloudPlatformService.listenToAgentAssistEventsForGenesysCloud();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "conversation-completed",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });
  });

  describe("fetchConversationName", () => {
    it("fetches conversation name successfully", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ conversationName: "test-conversation-name" })
      });

      const result =
        await genesysCloudPlatformService.fetchConversationName("test-key");

      expect(global.fetch).toHaveBeenCalledWith(
        "https://test-endpoint.com/conversation-name?conversationIntegrationKey=test-key",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: "test-token"
          },
          signal: expect.any(AbortSignal)
        }
      );
      expect(result).toBe("test-conversation-name");
    });

    it("returns null when conversation name not found (404)", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 404
      });

      const result =
        await genesysCloudPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
    });

    it("returns null when fetch fails with non-404 error", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error"
      });

      const result =
        await genesysCloudPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
      expect(mockLwc.debugLog).toHaveBeenCalledWith(
        "[AgentAssist] Error fetching conversation name: 500 Internal Server Error"
      );
    });

    it("returns null when network error occurs", async () => {
      global.fetch.mockRejectedValue(new Error("Network error"));

      const result =
        await genesysCloudPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
      expect(mockLwc.debugLog).toHaveBeenCalledWith(
        "[AgentAssist] Network error fetching conversation name: Network error"
      );
    });
  });

  describe("handleConversationEndedForGenesysCloud", () => {
    it("triggers summarization when the feature is enabled", () => {
      mockLwc.conversationName = "test-conversation-name";
      mockLwc.features = "CONVERSATION_SUMMARIZATION";

      genesysCloudPlatformService.handleConversationEndedForGenesysCloud();

      expect(mockLwc.triggerSummarization).toHaveBeenCalled();
    });

    it("does not trigger summarization when the feature is disabled", () => {
      mockLwc.conversationName = "test-conversation-name";
      mockLwc.features = "";

      genesysCloudPlatformService.handleConversationEndedForGenesysCloud();

      expect(mockLwc.triggerSummarization).not.toHaveBeenCalled();
    });

    it("starts polling for conversation name after handling conversation ended", () => {
      mockLwc.conversationName = "test-conversation-name";
      genesysCloudPlatformService.genesysConversationId = "test-genesys-id";

      const spy = jest.spyOn(
        genesysCloudPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      genesysCloudPlatformService.handleConversationEndedForGenesysCloud();

      expect(spy).toHaveBeenCalledWith("test-genesys-id");
    });
  });

  describe("extractConversationId", () => {
    it("returns null for empty or non-object payloads", () => {
      expect(
        genesysCloudPlatformService.extractConversationId(null)
      ).toBeNull();
      expect(genesysCloudPlatformService.extractConversationId("")).toBeNull();
      expect(
        genesysCloudPlatformService.extractConversationId(12345)
      ).toBeNull();
      expect(
        genesysCloudPlatformService.extractConversationId("invalid-uuid-string")
      ).toBeNull();
    });

    it("extracts UUID from plain UUID string", () => {
      const uuid = "12345678-1234-1234-1234-123456789abc";
      expect(genesysCloudPlatformService.extractConversationId(uuid)).toBe(
        uuid
      );
    });

    it("extracts UUID from conversationId field", () => {
      const uuid = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d";
      expect(
        genesysCloudPlatformService.extractConversationId({
          conversationId: uuid
        })
      ).toBe(uuid);
    });

    it("extracts UUID from interactionId field", () => {
      const uuid = "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e";
      expect(
        genesysCloudPlatformService.extractConversationId({
          interactionId: uuid
        })
      ).toBe(uuid);
    });

    it("extracts UUID from nested object structures", () => {
      const uuid = "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f";
      const payload = {
        data: {
          interaction: {
            id: uuid
          }
        }
      };
      expect(genesysCloudPlatformService.extractConversationId(payload)).toBe(
        uuid
      );
    });

    it("extracts UUID from array within payload", () => {
      const uuid = "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a";
      const payload = {
        interactions: [{ status: "connected" }, { id: uuid, state: "active" }]
      };
      expect(genesysCloudPlatformService.extractConversationId(payload)).toBe(
        uuid
      );
    });
  });

  describe("requestGenesysInteractions", () => {
    it("posts messages to window and parent windows safely without throwing", () => {
      const postMessageSpy = jest.spyOn(window, "postMessage");
      expect(() => {
        genesysCloudPlatformService.requestGenesysInteractions();
      }).not.toThrow();
      expect(postMessageSpy).toHaveBeenCalled();
    });
  });

  describe("pollForConversationNameByIntegrationKey", () => {
    it("returns immediately if conversationIntegrationKey is empty", () => {
      genesysCloudPlatformService.pollForConversationNameByIntegrationKey("");
      expect(mockLwc.debugLog).toHaveBeenCalledWith(
        "pollForConversationNameByIntegrationKey called with empty integration key"
      );
    });

    it("initializes UI modules when fetchConversationName succeeds", async () => {
      jest.useFakeTimers();
      const fetchSpy = jest
        .spyOn(genesysCloudPlatformService, "fetchConversationName")
        .mockResolvedValue("projects/test/locations/global/conversations/123");
      const initUIModulesSpy = jest.spyOn(
        genesysCloudPlatformService,
        "initUIModules"
      );
      const connectorInitSpy = jest.spyOn(
        genesysCloudPlatformService,
        "handleConnectorInitialized"
      );

      genesysCloudPlatformService.pollForConversationNameByIntegrationKey(
        "12345678-1234-1234-1234-123456789abc"
      );

      // Run microtasks
      await Promise.resolve();
      await Promise.resolve();

      expect(fetchSpy).toHaveBeenCalled();
      expect(genesysCloudPlatformService.lwc.conversationName).toBe(
        "projects/test/locations/global/conversations/123"
      );
      expect(connectorInitSpy).toHaveBeenCalled();
      expect(initUIModulesSpy).toHaveBeenCalled();
    });

    it("schedules next poll when conversationName is not found", async () => {
      jest.useFakeTimers();
      jest
        .spyOn(genesysCloudPlatformService, "fetchConversationName")
        .mockResolvedValue(null);

      genesysCloudPlatformService.pollForConversationNameByIntegrationKey(
        "12345678-1234-1234-1234-123456789abc",
        { initialDelay: 500, maxDelay: 2000 }
      );

      await Promise.resolve();
      await Promise.resolve();

      expect(genesysCloudPlatformService.pollingTimeout).toBeDefined();
    });
  });
});
