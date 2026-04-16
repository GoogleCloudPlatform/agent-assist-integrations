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

// Mock the message channels by creating a mock file in jest-mocks
// This approach avoids the module resolution issues
jest.mock('lightning/messageService');
import MessagingPlatformService from "../MessagingPlatformService";
import { subscribe, unsubscribe } from "lightning/messageService";
import { setupPlatformServiceTest, createMockLwcComponent, createMockRefs } from "../testUtils";

describe("MessagingPlatformService", () => {
  let mockLwc;
  let mockRefs;
  let messagingPlatformService;

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
      conversationId: "test-conversation-id",
      projectLocationName: "projects/test/locations/test",
      showTranscript: true,
      loadError: null,
      debugLog: jest.fn(),
      messageContext: "test-message-context",
      cancelSummarizationTimeout: null,
      triggerSummarization: jest.fn(),
      refs: {
        transcriptContainer: {
          classList: {
            add: jest.fn(),
            remove: jest.fn()
          }
        }
      }
    });

    mockRefs = createMockRefs({
      conversationToolkitApi: {
        setAgentInput: jest.fn()
      }
    });

    messagingPlatformService = new MessagingPlatformService(mockLwc, mockRefs);
  });

  afterEach(() => {});

  describe("constructor", () => {
    it("initializes with lwc and refs parameters", () => {
      expect(messagingPlatformService.lwc).toBe(mockLwc);
      expect(messagingPlatformService.refs).toBe(mockRefs);
    });
  });

  describe("init", () => {
    it("initializes the service by generating a conversation name and subscribing to events", () => {
      const generateSpy = jest.spyOn(
        messagingPlatformService,
        "generateConversationName"
      );
      const subscribeSpy = jest.spyOn(
        messagingPlatformService,
        "subscribeToMessageChannels"
      );
      const listenSpy = jest.spyOn(
        messagingPlatformService,
        "listenToAgentAssistEventsForMessaging"
      );
      expect(() => {
        messagingPlatformService.init();
      }).not.toThrow();
      expect(generateSpy).toHaveBeenCalled();
      expect(subscribeSpy).toHaveBeenCalled();
      expect(listenSpy).toHaveBeenCalled();
    });
  });

  describe("teardown", () => {
    it("executes without errors", () => {
      expect(() => messagingPlatformService.teardown()).not.toThrow();
    });
  });

  describe("listenToAgentAssistEventsForMessaging", () => {
    it("adds event listeners for smart-reply-selected", () => {
      messagingPlatformService.listenToAgentAssistEventsForMessaging();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "smart-reply-selected",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });

    it("adds event listeners for agent-coaching-response-selected", () => {
      messagingPlatformService.listenToAgentAssistEventsForMessaging();

      expect(global.addAgentAssistEventListener).toHaveBeenCalledWith(
        "agent-coaching-response-selected",
        expect.any(Function),
        { namespace: "test-record-id" }
      );
    });
  });

  describe("handleMessageSendForMessaging", () => {
    it("dispatches analyze-content-requested event when recordId matches", () => {
      const message = {
        recordId: "test-record-id",
        content: "test message content"
      };

      messagingPlatformService.handleMessageSendForMessaging(
        "HUMAN_AGENT",
        message
      );

      expect(global.dispatchAgentAssistEvent).toHaveBeenCalledWith(
        "analyze-content-requested",
        {
          detail: {
            conversationId: "test-conversation-id",
            participantRole: "HUMAN_AGENT",
            request: {
              textInput: { text: message.content, languageCode: "us" }
            }
          }
        },
        { namespace: "test-record-id" }
      );
    });

    it("does not dispatch event when recordId does not match", () => {
      const message = {
        recordId: "different-record-id",
        content: "test message content"
      };

      messagingPlatformService.handleMessageSendForMessaging(
        "HUMAN_AGENT",
        message
      );

      expect(global.dispatchAgentAssistEvent).not.toHaveBeenCalled();
    });
  });

  describe("handleAgentAssistEventForMessaging", () => {
    it("sets agent input when smart-reply-selected event is handled", async () => {
      const event = {
        detail: {
          answer: {
            reply: "test smart reply"
          }
        }
      };

      await messagingPlatformService.handleAgentAssistEventForMessaging(
        "smart-reply-selected",
        event
      );

      expect(
        mockRefs.conversationToolkitApi.setAgentInput
      ).toHaveBeenCalledWith("test-record-id", { text: "test smart reply" });
    });

    it("sets agent input when agent-coaching-response-selected event is handled", async () => {
      const event = {
        detail: {
          selectedResponse: "test coaching response"
        }
      };

      await messagingPlatformService.handleAgentAssistEventForMessaging(
        "agent-coaching-response-selected",
        event
      );

      expect(
        mockRefs.conversationToolkitApi.setAgentInput
      ).toHaveBeenCalledWith("test-record-id", {
        text: "test coaching response"
      });
    });
  });

  describe("generateConversationName", () => {
    it("generates conversation name with proper format", () => {
      messagingPlatformService.generateConversationName();

      expect(mockLwc.conversationId).toBe("SF-test-record-id");
      expect(mockLwc.conversationName).toBe(
        "projects/test/locations/test/conversations/SF-test-record-id"
      );
    });
  });

  describe("handleConversationEndedForMessaging", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("dispatches conversation-completed event when features include CONVERSATION_SUMMARIZATION", () => {
      const event = {
        recordId: "test-record-id",
      };

      messagingPlatformService.handleConversationEndedForMessaging(event);

      expect(global.dispatchAgentAssistEvent).toHaveBeenCalledWith(
        "conversation-completed",
        { detail: { conversationName: "test-conversation-name" } },
        { namespace: "test-record-id" }
      );
    });

    it("does not dispatch conversation-completed event when features do not include CONVERSATION_SUMMARIZATION", () => {
      mockLwc.features = "OTHER_FEATURE";
      const event = {
        recordId: "test-record-id",
      };

      messagingPlatformService.handleConversationEndedForMessaging(event);

      expect(global.dispatchAgentAssistEvent).not.toHaveBeenCalled();
    });

    it("does not dispatch conversation-completed event when recordId does not match", () => {
      const event = {
        recordId: "different-record-id",
      };

      messagingPlatformService.handleConversationEndedForMessaging(event);

      expect(global.dispatchAgentAssistEvent).not.toHaveBeenCalled();
    });

    it("should call triggerSummarization after a timeout", () => {
      const event = {
        recordId: "test-record-id",
      };

      messagingPlatformService.handleConversationEndedForMessaging(event);
      expect(mockLwc.triggerSummarization).not.toHaveBeenCalled();
      jest.runAllTimers();
      expect(mockLwc.triggerSummarization).toHaveBeenCalled();
    });
  });
  describe("unsubscribeFromMessagingChannels", () => {
    it("should unsubscribe from all message channels", () => {
      messagingPlatformService.subscribeToMessageChannels();
      messagingPlatformService.unsubscribeFromMessagingChannels();
      expect(unsubscribe).toHaveBeenCalledTimes(4);
      expect(messagingPlatformService.subscriptions.length).toBe(0);
    });
  });

  describe("handleTabClosedForMessaging", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });
    it("should clear the timeout", () => {
      const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");
      mockLwc.cancelSummarizationTimeout = setTimeout(jest.fn(), 500);
      messagingPlatformService.handleTabClosedForMessaging({});
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
    it("should not clear the timeout if cancelSummarizationTimeout is not set", () => {
      const clearTimeoutSpy = jest.spyOn(global, "clearTimeout");
      messagingPlatformService.handleTabClosedForMessaging({});
      expect(clearTimeoutSpy).not.toHaveBeenCalled();
    });
  });
});