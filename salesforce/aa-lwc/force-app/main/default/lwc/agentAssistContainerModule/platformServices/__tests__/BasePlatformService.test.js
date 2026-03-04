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

import BasePlatformService from "../BasePlatformService";
import { setupPlatformServiceTest, createMockLwcComponent, createMockRefs } from "../testUtils";

describe("BasePlatformService", () => {
  let mockLwc;
  let mockRefs;
  let basePlatformService;

  setupPlatformServiceTest();

  beforeEach(() => {
    jest.clearAllMocks();

    mockLwc = createMockLwcComponent({
      consumerKey: "test-key",
      consumerSecret: "test-secret",
      endpoint: "https://test-endpoint.com",
      recordId: "test-record-id",
      channel: "chat",
      features: "CONVERSATION_SUMMARIZATION",
      conversationProfile:
        "projects/test/locations/test/conversationProfiles/test",
      debugMode: false,
      token: "test-token",
      conversationName: "test-conversation-name",
      showTranscript: true,
      loadError: null,
      debugLog: jest.fn(),
      triggerSummarization: jest.fn(),
      cancelSummarizationTimeout: jest.fn(),
      messageContext: {},
      refs: {
        transcriptContainer: {
          classList: {
            add: jest.fn(),
            remove: jest.fn()
          }
        },
        agentAssistContainer: {
          appendChild: jest.fn(),
          classList: {
            remove: jest.fn()
          }
        },
        agentAssistTranscript: {
          appendChild: jest.fn()
        }
      }
    });

    mockRefs = createMockRefs();

    basePlatformService = new BasePlatformService(mockLwc, mockRefs);
  });

  afterEach(() => {
    // Ensure fake timers from a test don't leak into subsequent tests.
    jest.useRealTimers();
  });

  describe("constructor", () => {
    it("initializes with lwc and refs parameters", () => {
      expect(basePlatformService.lwc).toBe(mockLwc);
      expect(basePlatformService.refs).toBe(mockRefs);
    });
  });

  describe("init", () => {
    it("executes without errors", () => {
      expect(() => {
        basePlatformService.init();
      }).not.toThrow();
    });
  });

  describe("teardown", () => {
    it("executes without errors", () => {
      expect(() => {
        basePlatformService.teardown();
      }).not.toThrow();
    });
  });

  describe("registerAuthToken", () => {
    let errorSpy;

    beforeEach(() => {
      // Suppress console.error output for tests that intentionally trigger errors.
      errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    });

    afterEach(() => {
      errorSpy.mockRestore();
    });

    it("registers auth token successfully", async () => {
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: "test-access-token" })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ token: "test-ui-connector-token" })
        });

      const result = await basePlatformService.registerAuthToken();

      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect(result).toBe("test-ui-connector-token");
    });

    it("handles OAuth token request failure", async () => {
      // This test verifies that a failed OAuth token request is handled gracefully.
      global.fetch.mockResolvedValueOnce({
        ok: false,
        statusText: "OAuth failed"
      });

      const result = await basePlatformService.registerAuthToken();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(result).toBeNull();
      expect(mockLwc.loadError).toBeInstanceOf(Error);
    });

    it("handles UI Connector registration failure", async () => {
      // This test verifies that a failed UI Connector registration is handled gracefully.
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: "test-access-token" })
        })
        .mockResolvedValueOnce({
          ok: false,
          statusText: "Bad Request"
        });

      const result = await basePlatformService.registerAuthToken();

      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect(result).toBeNull();
      expect(mockLwc.loadError).toBeInstanceOf(Error);
    });
  });

  describe("initUIModules", () => {
    beforeEach(() => {
      global.document.createElement = jest.fn((tagName) => {
        if (tagName === "agent-assist-transcript") {
          return {
            setAttribute: jest.fn(),
            classList: { add: jest.fn() }
          };
        }
        if (tagName === "agent-assist-ui-modules-v2") {
          return {
            setAttribute: jest.fn(),
            classList: { add: jest.fn() },
            generalConfig: {}
          };
        }
        return {};
      });

      global.UiModulesConnector = jest.fn(() => ({
        init: jest.fn()
      }));

      global.navigator.clipboard = {
        writeText: jest.fn()
      };
    });

    it("initializes UI modules correctly", () => {
      basePlatformService.initUIModules();

      expect(global.document.createElement).toHaveBeenCalledWith(
        "agent-assist-transcript"
      );
      expect(global.document.createElement).toHaveBeenCalledWith(
        "agent-assist-ui-modules-v2"
      );
      expect(mockLwc.refs.agentAssistContainer.appendChild).toHaveBeenCalled();
    });

    it("does not create transcript if showTranscript is false", () => {
      mockLwc.showTranscript = false;
      basePlatformService = new BasePlatformService(mockLwc, mockRefs);

      basePlatformService.initUIModules();

      expect(global.document.createElement).toHaveBeenCalledWith(
        "agent-assist-ui-modules-v2"
      );
      expect(global.document.createElement).not.toHaveBeenCalledWith(
        "agent-assist-transcript"
      );
    });
  });

  describe("createRequestOptions", () => {
    it("creates request options with proper headers", () => {
      const options = basePlatformService.createRequestOptions("GET");

      expect(options.method).toBe("GET");
      expect(options.headers).toEqual({
        "Content-Type": "application/json",
        Authorization: "test-token"
      });
    });

    it("includes body when provided", () => {
      const options = basePlatformService.createRequestOptions(
        "POST",
        "test-body"
      );

      expect(options.body).toBe("test-body");
    });
  });

  describe("initAgentAssistEvents", () => {
    it("adds event listeners for chat channel", () => {
      mockLwc.channel = "chat";
      basePlatformService.initAgentAssistEvents();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "api-connector-initialized",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });

    it("adds event listeners for voice channel", () => {
      mockLwc.channel = "voice";
      basePlatformService.initAgentAssistEvents();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "event-based-connector-initialized",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });

    it("adds event listeners for copy-to-clipboard", () => {
      basePlatformService.initAgentAssistEvents();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "copy-to-clipboard",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });

    it("adds event listeners for dark-mode-toggled", () => {
      basePlatformService.initAgentAssistEvents();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "dark-mode-toggled",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });
  });

  describe("handleConnectorInitialized", () => {
    beforeEach(() => {
      jest
        .spyOn(basePlatformService, "pollDialogflowForConversationExistence")
        .mockResolvedValue(true);
    });

    it("does not poll for conversation existence when channel is chat", async () => {
      mockLwc.channel = "chat";
      mockLwc.token = "test-token";
      mockLwc.conversationName = "test-conversation";

      await basePlatformService.handleConnectorInitialized();

      expect(
        basePlatformService.pollDialogflowForConversationExistence
      ).not.toHaveBeenCalled();
      expect(global.dispatchAgentAssistEvent).toHaveBeenCalledWith(
        "active-conversation-selected",
        { detail: { conversationName: "test-conversation" } },
        { namespace: "test-record-id" }
      );
    });

    it("waits for token and polls for conversation existence when channel is voice", async () => {
      mockLwc.channel = "voice";
      mockLwc.token = "test-token";
      mockLwc.conversationName = "test-conversation";

      await basePlatformService.handleConnectorInitialized();

      expect(
        basePlatformService.pollDialogflowForConversationExistence
      ).toHaveBeenCalled();
      expect(global.dispatchAgentAssistEvent).toHaveBeenCalledWith(
        "active-conversation-selected",
        { detail: { conversationName: "test-conversation" } },
        { namespace: "test-record-id" }
      );
    });
  });

  describe("pollDialogflowForConversationExistence", () => {
    it("succeeds when conversation exists", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        status: 200
      });

      const result =
        await basePlatformService.pollDialogflowForConversationExistence(3, 10);

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(result).toBe(true);
    });

    it("fails after max retries", async () => {
      jest.useFakeTimers();
      global.fetch.mockResolvedValue({
        ok: false,
        status: 404
      });

      const pollPromise =
        basePlatformService.pollDialogflowForConversationExistence(2, 10);

      // Fast-forward timers to simulate the polling delay and resolve the promise.
      await jest.runAllTimersAsync();
      const result = await pollPromise;

      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect(result).toBe(false);
    });
  });

  describe("deleteConversationName", () => {
    it("deletes conversation name successfully", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({})
      });

      await basePlatformService.deleteConversationName("test-key");

      expect(global.fetch).toHaveBeenCalledWith(
        "https://test-endpoint.com/conversation-name?conversationIntegrationKey=test-key",
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: "test-token"
          }
        }
      );
    });
  });

  describe("fetchConversationLifecycleState", () => {
    it("fetches conversation lifecycle state", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ lifecycleState: "ACTIVE" })
      });

      const result =
        await basePlatformService.fetchConversationLifecycleState();

      expect(global.fetch).toHaveBeenCalledWith(
        "https://test-endpoint.com/v2/test-conversation-name",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: "test-token"
          }
        }
      );
      expect(result).toBe("ACTIVE");
    });
  });

  describe("handleCopyToClipboard", () => {
    it("copies text to clipboard", async () => {
      // Mock navigator.clipboard for the jsdom environment, as it's not implemented.
      global.navigator.clipboard = {
        writeText: jest.fn().mockResolvedValue(undefined)
      };
      const mockEvent = { detail: { textToCopy: "test text" } };

      await basePlatformService.handleCopyToClipboard(mockEvent);

      expect(global.navigator.clipboard.writeText).toHaveBeenCalledWith(
        "test text"
      );
    });
  });

  describe("handleDarkModeToggled", () => {
    it("adds dark mode class when toggled on", () => {
      const mockEvent = { detail: { on: true } };

      basePlatformService.handleDarkModeToggled(mockEvent);

      expect(
        mockLwc.refs.transcriptContainer.classList.add
      ).toHaveBeenCalledWith("dark-mode");
    });

    it("removes dark mode class when toggled off", () => {
      const mockEvent = { detail: { on: false } };

      basePlatformService.handleDarkModeToggled(mockEvent);

      expect(
        mockLwc.refs.transcriptContainer.classList.remove
      ).toHaveBeenCalledWith("dark-mode");
    });
  });

  describe("isConversationCompleted", () => {
    it("detects completed conversation and deletes key", async () => {
      jest
        .spyOn(basePlatformService, "fetchConversationLifecycleState")
        .mockResolvedValue("COMPLETED");
      jest
        .spyOn(basePlatformService, "deleteConversationName")
        .mockResolvedValue(undefined);

      const result =
        await basePlatformService.isConversationCompleted("test-key");

      expect(
        basePlatformService.fetchConversationLifecycleState
      ).toHaveBeenCalled();
      expect(basePlatformService.deleteConversationName).toHaveBeenCalledWith(
        "test-key"
      );
      expect(result).toBe(true);
    });

    it("returns false for non-completed conversation", async () => {
      jest
        .spyOn(basePlatformService, "fetchConversationLifecycleState")
        .mockResolvedValue("ACTIVE");

      const result =
        await basePlatformService.isConversationCompleted("test-key");

      expect(
        basePlatformService.fetchConversationLifecycleState
      ).toHaveBeenCalled();
      expect(result).toBe(false);
    });
  });

  describe("initEventDragnet", () => {
    it("adds event listeners for all agent assist events", () => {
      basePlatformService.initEventDragnet();

      expect(global.addAgentAssistEventListener).toHaveBeenCalled();
    });
  });
});
