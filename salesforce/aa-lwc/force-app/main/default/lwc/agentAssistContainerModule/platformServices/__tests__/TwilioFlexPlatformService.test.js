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

import TwilioFlexPlatformService from "../TwilioFlexPlatformService";
import {
  setupPlatformServiceTest,
  createMockLwcComponent,
  createMockRefs
} from "../testUtils";

describe("TwilioFlexPlatformService", () => {
  let mockLwc;
  let mockRefs;
  let twilioFlexPlatformService;

  setupPlatformServiceTest();

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();

    // Create mock LWC component
    mockLwc = createMockLwcComponent();

    // Create mock refs
    mockRefs = createMockRefs();

    // Create instance of TwilioFlexPlatformService
    twilioFlexPlatformService = new TwilioFlexPlatformService(
      mockLwc,
      mockRefs
    );
  });

  afterEach(() => {});

  describe("constructor", () => {
    it("initializes with lwc and refs parameters", () => {
      expect(twilioFlexPlatformService.lwc).toBe(mockLwc);
      expect(twilioFlexPlatformService.refs).toBe(mockRefs);
      expect(
        twilioFlexPlatformService.handleConversationEndedForTwilioFlex
      ).toBeDefined();
    });
  });

  describe("init", () => {
    it("executes without errors", () => {
      expect(() => {
        twilioFlexPlatformService.init();
      }).not.toThrow();
    });

    it("logs initTwilioFlex call", () => {
      twilioFlexPlatformService.init();
      expect(mockLwc.debugLog).toHaveBeenCalledWith("initTwilioFlex called");
    });

    it("fetches conversation name when conversationName is not set", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ conversationName: "test-conversation-name" })
      });

      await twilioFlexPlatformService.init();

      expect(global.fetch).toHaveBeenCalledWith(
        "https://test-endpoint.com/conversation-name?conversationIntegrationKey=test-contact-phone",
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
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ conversationName: null })
      });

      const spy = jest.spyOn(
        twilioFlexPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      await twilioFlexPlatformService.init();

      expect(spy).toHaveBeenCalled();
    });
  });

  describe("teardown", () => {
    it("executes without errors", () => {
      expect(() => {
        twilioFlexPlatformService.teardown();
      }).not.toThrow();
    });

    it("clears polling timeout", () => {
      twilioFlexPlatformService.pollingTimeout = "some-timeout";
      const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");

      twilioFlexPlatformService.teardown();

      expect(clearTimeoutSpy).toHaveBeenCalledWith("some-timeout");
    });
  });

  describe("listenToAgentAssistEventsForTwilioFlex", () => {
    it("adds event listener for conversation-completed", () => {
      twilioFlexPlatformService.listenToAgentAssistEventsForTwilioFlex();

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
        await twilioFlexPlatformService.fetchConversationName("test-key");

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
        await twilioFlexPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
    });

    it("returns null when fetch fails with non-404 error", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error"
      });

      const result =
        await twilioFlexPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
      expect(mockLwc.debugLog).toHaveBeenCalledWith(
        "Error fetching conversation name: 500 Internal Server Error"
      );
    });

    it("returns null when network error occurs", async () => {
      global.fetch.mockRejectedValue(new Error("Network error"));

      const result =
        await twilioFlexPlatformService.fetchConversationName("test-key");

      expect(result).toBeNull();
      expect(mockLwc.debugLog).toHaveBeenCalledWith(
        "Network error fetching conversation name: Network error"
      );
    });
  });

  describe("handleConversationEndedForTwilioFlex", () => {
    it("triggers summarization when the feature is enabled", () => {
      mockLwc.conversationName = "test-conversation-name";
      mockLwc.features = "CONVERSATION_SUMMARIZATION";

      twilioFlexPlatformService.handleConversationEndedForTwilioFlex();

      expect(mockLwc.triggerSummarization).toHaveBeenCalled();
    });

    it("does not trigger summarization when the feature is disabled", () => {
      mockLwc.features = ""; // Ensure the feature is not present
      twilioFlexPlatformService.handleConversationEndedForTwilioFlex();
      expect(mockLwc.triggerSummarization).not.toHaveBeenCalled();
    });

    it("starts polling for conversation name after handling conversation ended", () => {
      mockLwc.conversationName = "test-conversation-name";

      const spy = jest.spyOn(
        twilioFlexPlatformService,
        "pollForConversationNameByIntegrationKey"
      );

      twilioFlexPlatformService.handleConversationEndedForTwilioFlex();

      expect(spy).toHaveBeenCalledWith("test-contact-phone");
    });
  });
});
