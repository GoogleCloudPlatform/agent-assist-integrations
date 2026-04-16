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

/**
 * Common test setup for platform services
 */
export const setupPlatformServiceTest = () => {
  beforeAll(() => {
    global.fetch = jest.fn();
    global.document = {
      createElement: jest.fn(),
      body: {
        classList: {
          contains: jest.fn(),
          add: jest.fn(),
          remove: jest.fn()
        }
      }
    };
    global.UiModulesConnector = jest.fn();
    global.addAgentAssistEventListener = jest.fn();
    global.dispatchAgentAssistEvent = jest.fn();
    global.navigator = {
      clipboard: {
        writeText: jest.fn()
      }
    };
    global.MessageContext = jest.fn();
    global.subscribe = jest.fn();
    global.unsubscribe = jest.fn();
    global.setTimeout = jest.fn();
    global.clearTimeout = jest.fn();
    global.window = {
      setTimeout: jest.fn(),
      clearTimeout: jest.fn()
    };
  });

  afterAll(() => {
    delete global.fetch;
    delete global.document;
    delete global.UiModulesConnector;
    delete global.addAgentAssistEventListener;
    delete global.dispatchAgentAssistEvent;
    delete global.navigator;
    delete global.MessageContext;
    delete global.subscribe;
    delete global.unsubscribe;
    delete global.setTimeout;
    delete global.clearTimeout;
    delete global.window;
  });
};

/**
 * Creates a standard mock LWC component for platform service tests
 */
export const createMockLwcComponent = (overrides = {}) => {
  return {
    contactPhone: "test-contact-phone",
    platform: "twilioflex",
    projectLocationName: "projects/test/locations/test",
    conversationId: null,
    conversationName: null,
    debugMode: false,
    debugLog: jest.fn(),
    recordId: "test-record-id",
    features: "CONVERSATION_SUMMARIZATION",
    conversationProfile:
      "projects/test/locations/test/conversationProfiles/test",
    token: "test-token",
    endpoint: "https://test-endpoint.com",
    consumerKey: "test-key",
    consumerSecret: "test-secret",
    channel: "voice",
    showTranscript: true,
    loadError: null,
    triggerSummarization: jest.fn(),
    refs: {
      transcriptContainer: {
        classList: {
          add: jest.fn(),
          remove: jest.fn()
        }
      }
    },
    ...overrides
  };
};

/**
 * Creates a mock platform service for jest.
 */
export const createMockPlatformService = () => {
  const mock = jest.fn().mockImplementation(() => {
    return {
      init: jest.fn().mockResolvedValue(undefined),
      initAgentAssistEvents: jest.fn(),
      initEventDragnet: jest.fn(),
      teardown: jest.fn(),
      registerAuthToken: jest.fn().mockResolvedValue("mock-token")
    };
  });
  return { __esModule: true, default: mock };
};

/**
 * Creates a standard mock refs object for platform service tests
 */
export const createMockRefs = (overrides = {}) => {
  return {
    agentAssistTranscript: {
      appendChild: jest.fn()
    },
    agentAssistContainer: {
      appendChild: jest.fn()
    },
    transcriptContainer: {
      classList: {
        add: jest.fn(),
        remove: jest.fn()
      }
    },
    ...overrides
  };
};
