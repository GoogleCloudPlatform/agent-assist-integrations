// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// @ts-nocheck
import Cookies from 'js-cookie';
import { io } from 'socket.io-client';

import { ConnectorConfig, UiModuleConnector, UiModuleEventBasedConnector } from '../../types/AgentAssist';
import { getCustomApiEndpoint, getConversationProfile } from '../../config';
import logger from '../../../../utils/logger';

/**
 * Service for managing the Agent Assist UI Modules.
 * @class
 */
class AgentAssistUtils {
  static #agentAssistUtils: AgentAssistUtils;

  static #connector: UiModuleConnector;

  /**
   * The Singleton's constructor should always be private to prevent direct
   * construction calls with the `new` operator.
   */
  private constructor() {}

  /**
   * The static getter that controls access to the singleton instance.
   *
   * This implementation allows you to extend the Singleton class while
   * keeping just one instance of each subclass around.
   */
  public static get instance(): AgentAssistUtils {
    if (!AgentAssistUtils.#agentAssistUtils) {
      AgentAssistUtils.#agentAssistUtils = new AgentAssistUtils();
    }
    logger.debug('[Agent-Assist] connector already instantiated');
    return AgentAssistUtils.#agentAssistUtils;
  }

  /**
   *  Makes sure the conversation profile is correctly formatted
   * @param {string} conversationProfile the conversation profile name that is being checked.
   * @returns {boolean} value to determine if the conversation profile name is valid or not.
   */
  static validateConversationProfile = (conversationProfile: string): boolean => {
    const regExp = new RegExp('(^projects/[^/]+/locations/[^/]+)/conversationProfiles/[^/]+$');
    return regExp.test(conversationProfile);
  };

  /**
   * Initialize the UI module connectors.
   * @param {ConnectorConfig} config configuration to initialize the ui modules.
   * See {@link https://cloud.google.com/agent-assist/docs/ui-modules#implement_the_ui_module_connector Implement the UI module connector}.
   */
  public initializeUiConnector(config: ConnectorConfig) {
    if (!AgentAssistUtils.#connector) {
      AgentAssistUtils.#connector = new UiModulesConnector();
      window._uiModuleFlags = { debug: false };
      logger.debug('[Agent-Assist] connector instantiated');
    }
    AgentAssistUtils.#connector.init(config);
  }

  /**
   * Retrieves JWT token from backend service
   * @param {string} token CCaaS platform token for the agent.
   * @returns {string} JWT token to authenticate with the UI connector backend.
   */
  public async getAgentAssistAuthToken(token: string, customApiEndpoint?: string): string {
    const authToken = Cookies.get('CCAI_AGENT_ASSIST_AUTH_TOKEN');
    if (authToken) {
      logger.debug('[Agent-Assist] AuthToken retrieved from cookies');
      return authToken;
    }

    logger.debug('[Agent-Assist] Making request for Agent Assist auth token');
    const endpoint = this.validateUrl(customApiEndpoint ? customApiEndpoint : getCustomApiEndpoint());
    return fetch(`${endpoint}/register`, {
      method: 'POST',
      headers: [['Authorization', token]],
    })
      .then(async (response) => {
        if (!response.ok) {
          // error coming back from server
          throw Error('could not fetch the data for that resource');
        }
        return response.json();
      })
      .then((data) => {
        logger.debug('[Agent-Assist] Saving auth token in cookie');
        Cookies.set('CCAI_AGENT_ASSIST_AUTH_TOKEN', data.token, { expires: 7 });
        return data.token;
      });
  }

  /**
   * Sets the authtoken without reiniting the UI modules
   * @param {string} authToken authtoken provided by the UIM backend.
   */
  public setAgentAssistAuthToken(authToken: string) {
    AgentAssistUtils.#connector.setAuthToken(authToken);
    Cookies.set('CCAI_AGENT_ASSIST_AUTH_TOKEN', authToken, { expires: 7 });
  }

  /**
   * Generate the conversation name based off the conversation profile string.
   * @param {string} conversationId ID for the specific conversation.
   * @returns {string} The full conversation profile name.
   */
  public getConversationName(conversationId: string): string {
    const [, projectLocation] =
      getConversationProfile().match(/(^projects\/[^/]+\/locations\/[^/]+)\/conversationProfiles\/[^/]+$/) || [];
    return `${projectLocation}/conversations/${conversationId}`;
  }

  /**
   * Returns the name of the conversation profile which validates it is created and the UI
   * moudle connector backend has access to the resource.
   * @param {string} conversationProfileName The full conversation profile name.
   * @param {string} customApiEndpoint Url where the UI module connector backend is located.
   * @returns {string} returns the name of the conversation profile.
   */
  public getConversationProfile(conversationProfileName: string, customApiEndpoint?: string): string {
    const authToken = Cookies.get('CCAI_AGENT_ASSIST_AUTH_TOKEN');
    if (!authToken) {
      logger.debug('[Agent-Assist] No auth token stored, retrieve auth token before making CES request');
      return undefined;
    }
    const endpoint = this.validateUrl(customApiEndpoint ? customApiEndpoint : getCustomApiEndpoint());
    return fetch(`${endpoint}/v2beta1/${conversationProfileName}`, {
      method: 'GET',
      headers: [['Authorization', authToken]],
    })
      .then(async (response) => {
        if (!response.ok) {
          // error coming back from server
          throw Error('could not fetch the data for that resource');
        }
        return response.json();
      })
      .then((data) => {
        logger.debug('[Agent-Assist] Conversation profile retrived');
        return data.name;
      });
  }

  /**
   * Gets the status of the UI module connector backend.
   * @param {string} customApiEndpoint Url where the UI module connector backend is located.
   * @returns {boolean} Value to determine if the UI module connector backend is up.
   */
  public getStatus(customApiEndpoint?: string): boolean {
    const endpoint = this.validateUrl(customApiEndpoint ? customApiEndpoint : getCustomApiEndpoint());
    return fetch(`${endpoint}/status`, {
      method: 'GET',
    })
      .then((response) => {
        return response.ok;
      })
      .catch(() => {
        return false;
      });
  }

  /**
   * Gets the status of the UI module connector backend websocket.
   * @param {string} notifierServerEndpoint Notifier server endpoint where the UI module connector backend websocket is located.
   * @param {any} onSuccess function to fire when the websocket status is up
   * @param {any} onError function to fire when the websocket status is down
   * @returns {void}
   */
  public getWebsocketStatus(notifierServerEndpoint: string, onSuccess: any, onError: any): void {
    const endpoint = this.validateUrl(notifierServerEndpoint);
    const token = Cookies.get('CCAI_AGENT_ASSIST_AUTH_TOKEN');
    if (!token) {
      logger.debug('[Agent-Assist] No auth token stored, retrieve auth token before making CES request');
      return;
    }
    try {
      const socket = io(endpoint, {
        auth: {
          token,
        },
      });

      socket.on('connect_error', (err) => {
        logger.debug(`[Agent-Assist] connect_error due to ${err.message}`);
        onError();
        socket.close();
      });

      socket.on('connect', () => {
        logger.debug('[Agent-Assist] Websocket connection successful');
        onSuccess();
        socket.close();
      });

      socket.on('unauthenticated', () => {
        logger.debug('[Agent-Assist] Websocket unauthenticated');
        onError();
        socket.close();
      });
    } catch (error) {
      logger.debug('Network Error');
      onError();
    }
  }

  public subscribeToConversation(conversationName: string): void {
    if (AgentAssistUtils.#connector) {
      AgentAssistUtils.#connector.subscribeToEventBasedConversation(conversationName);
    }
  }

  /**
   * Validates a url and adds protocal prefix to url string.
   * @param {string} url string representing a url.
   * @returns {string} url string with the protocal prefixed to the string.
   */
  private validateUrl(url: string): string {
    const protocalRegExp = new RegExp('^(http|https)://');
    const hasProtocal = protocalRegExp.test(url);
    return `${hasProtocal ? '' : 'https://'}${url}`;
  }
}

export default AgentAssistUtils;
