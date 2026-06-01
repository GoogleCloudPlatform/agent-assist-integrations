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

import * as Flex from '@twilio/flex-ui';
import Cookies from 'js-cookie';
import { io, mockSocket } from 'socket.io-client';

import AgentAssistUtils from './AgentAssistUtils';
import logger from '../../../../utils/logger';

describe('AgentAssistUtils', () => {
  describe('instantiation', () => {
    it('should return an instance of AgentAssistUtils', () => {
      const agentAssistUtils = AgentAssistUtils.instance;

      expect(agentAssistUtils).not.toBeUndefined();
    });

    it('should not instantiate a new instance after one has been defined', () => {
      const loggerSpy = jest.spyOn(logger, 'debug');

      const agentAssistUtils = AgentAssistUtils.instance;

      expect(agentAssistUtils).not.toBeUndefined();
      expect(loggerSpy).toBeCalledWith('[Agent-Assist] connector already instantiated');
    });
  });

  describe('API Calls', () => {
    let agentAssistUtils;

    beforeAll(() => {
      agentAssistUtils = AgentAssistUtils.instance;
    });

    describe('getStatus', () => {
      it('should return true when the backend service return 200', async () => {
        fetch.mockResponseOnce('Hello, cross-origin-world!');

        const isUp = await agentAssistUtils.getStatus('https://8.8.8.8');

        expect(isUp).toBe(true);
        expect(fetch).toHaveBeenCalledWith('https://8.8.8.8/status', { method: 'GET' });
      });

      it('should return false when the backend service does not return 200', async () => {
        fetch.mockResponseOnce('', { status: 500 });

        const isUp = await agentAssistUtils.getStatus('https://8.8.8.8');

        expect(isUp).toBe(false);
        expect(fetch).toHaveBeenCalledWith('https://8.8.8.8/status', { method: 'GET' });
      });

      it('should return false when promise is rejected', async () => {
        fetch.mockReject(async () => Promise.reject('API is down'));

        const isUp = await agentAssistUtils.getStatus('https://8.8.8.8');

        expect(isUp).toBe(false);
        expect(fetch).toHaveBeenCalledWith('https://8.8.8.8/status', { method: 'GET' });
      });

      it('should call the domain stored in the service configuration when no endpoint is passed', async () => {
        fetch.mockResponseOnce('Hello, cross-origin-world!');

        const { custom_data } = Flex.Manager.getInstance().configuration;
        const { custom_api_endpoint } = custom_data.features.agent_assist;

        const isUp = await agentAssistUtils.getStatus();

        expect(isUp).toBe(true);
        expect(fetch).toHaveBeenCalledWith(`https://${custom_api_endpoint}/status`, { method: 'GET' });
      });

      it('should default to https when protocal is not passed in the provided domain', async () => {
        fetch.mockResponseOnce('Hello, cross-origin-world!');

        const isUp = await agentAssistUtils.getStatus('8.8.8.8');

        expect(isUp).toBe(true);
        expect(fetch).toHaveBeenCalledWith('https://8.8.8.8/status', { method: 'GET' });
      });

      it('should allow http as the protocal when passed in the domain', async () => {
        fetch.mockResponseOnce('Hello, cross-origin-world!');

        const isUp = await agentAssistUtils.getStatus('http://8.8.8.8');

        expect(isUp).toBe(true);
        expect(fetch).toHaveBeenCalledWith('http://8.8.8.8/status', { method: 'GET' });
      });
    });

    describe('getAgentAssistAuthToken', () => {
      it('Should retrieve token is cookie is present', async () => {
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');
        const loggerSpy = jest.spyOn(logger, 'debug');

        const authToken = await agentAssistUtils.getAgentAssistAuthToken('mockAgentToken');

        expect(authToken).toBe('mockAuthToken');
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] AuthToken retrieved from cookies');
      });

      it('Should make an API call to get token when none is present', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        fetch.mockResponseOnce(JSON.stringify({ token: 'mockAuthToken' }));
        const { custom_data } = Flex.Manager.getInstance().configuration;
        const { custom_api_endpoint } = custom_data.features.agent_assist;

        const authToken = await agentAssistUtils.getAgentAssistAuthToken('mockAgentToken');

        expect(authToken).toBe('mockAuthToken');
        expect(loggerSpy).toBeCalledTimes(2);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] Making request for Agent Assist auth token');
        expect(fetch).toHaveBeenCalledWith(`https://${custom_api_endpoint}/register`, {
          method: 'POST',
          headers: [['Authorization', 'mockAgentToken']],
        });
      });

      it('Should save auth token in a cookie when retrieved from the backend', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        const cookiesSpy = jest.spyOn(Cookies, 'set');
        fetch.mockResponseOnce(JSON.stringify({ token: 'mockAuthToken' }));

        await agentAssistUtils.getAgentAssistAuthToken('mockAgentToken');

        expect(loggerSpy).toBeCalledTimes(2);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] Saving auth token in cookie');
        expect(cookiesSpy).toBeCalledTimes(1);
        expect(cookiesSpy).toBeCalledWith('CCAI_AGENT_ASSIST_AUTH_TOKEN', 'mockAuthToken', { expires: 7 });
      });
    });

    describe('getConversationProfile', () => {
      it('Should return undefined if no auth token is present in the cookies', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');

        const conversationProfile = await agentAssistUtils.getConversationProfile('mockConversationProfile');

        expect(conversationProfile).toBe(undefined);
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith(
          '[Agent-Assist] No auth token stored, retrieve auth token before making CES request',
        );
      });

      it('Should use the custom api endpoint in the service configuration if none is passed', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        fetch.mockResponseOnce(JSON.stringify({ name: 'mockConversationProfile' }));
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        const { custom_data } = Flex.Manager.getInstance().configuration;
        const { custom_api_endpoint } = custom_data.features.agent_assist;

        const conversationProfile = await agentAssistUtils.getConversationProfile('mockConversationProfile');

        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] Conversation profile retrived');
        expect(conversationProfile).toBe('mockConversationProfile');
        expect(fetch).toBeCalledWith(`https://${custom_api_endpoint}/v2beta1/mockConversationProfile`, {
          method: 'GET',
          headers: [['Authorization', 'mockAuthToken']],
        });
      });

      it('Should use endpoint passed if passed in function call', async () => {
        fetch.mockResponseOnce(JSON.stringify({ name: 'mockConversationProfile' }));
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getConversationProfile('mockConversationProfile', 'https://8.8.8.8');

        expect(fetch).toBeCalledWith(`https://8.8.8.8/v2beta1/mockConversationProfile`, {
          method: 'GET',
          headers: [['Authorization', 'mockAuthToken']],
        });
      });

      it('Should allow http to be used as the protocal is defined in endpoint', async () => {
        fetch.mockResponseOnce(JSON.stringify({ name: 'mockConversationProfile' }));
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getConversationProfile('mockConversationProfile', 'http://8.8.8.8');

        expect(fetch).toBeCalledWith(`http://8.8.8.8/v2beta1/mockConversationProfile`, {
          method: 'GET',
          headers: [['Authorization', 'mockAuthToken']],
        });
      });

      it('Should default https if no protocal is defined in endpoint', async () => {
        fetch.mockResponseOnce(JSON.stringify({ name: 'mockConversationProfile' }));
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getConversationProfile('mockConversationProfile', '8.8.8.8');

        expect(fetch).toBeCalledWith(`https://8.8.8.8/v2beta1/mockConversationProfile`, {
          method: 'GET',
          headers: [['Authorization', 'mockAuthToken']],
        });
      });
    });

    describe('getWebsocketStatus', () => {
      it('Should return undefined if no auth token is present in the cookies', () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();

        agentAssistUtils.getWebsocketStatus('mockNotifierServerEndpoint', onSuccessMock, onErrorMock);
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith(
          '[Agent-Assist] No auth token stored, retrieve auth token before making CES request',
        );
        expect(io).toBeCalledTimes(0);
      });

      it('Should allow http to be used as the protocal is defined in endpoint', async () => {
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        agentAssistUtils.getWebsocketStatus('http://mockNotifierServerEndpoint', onSuccessMock, onErrorMock);

        expect(io).toBeCalledTimes(1);
        expect(io).toBeCalledWith('http://mockNotifierServerEndpoint', { auth: { token: 'mockAuthToken' } });
      });

      it('Should default https if no protocal is defined in endpoint', async () => {
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        agentAssistUtils.getWebsocketStatus('mockNotifierServerEndpoint', onSuccessMock, onErrorMock);

        expect(io).toBeCalledTimes(1);
        expect(io).toBeCalledWith('https://mockNotifierServerEndpoint', { auth: { token: 'mockAuthToken' } });
      });

      it('should call onSuccess when websocket server emits connect', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getWebsocketStatus('mockNotifierServerEndpoint', onSuccessMock, onErrorMock);
        mockSocket.on.mock.calls[1][1]();

        expect(onSuccessMock).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] Websocket connection successful');
      });

      it('should call onError when websocket server emits unauthenticated', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getWebsocketStatus('mockNotifierServerEndpoint', onSuccessMock, onErrorMock);
        mockSocket.on.mock.calls[2][1]();

        expect(onErrorMock).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] Websocket unauthenticated');
      });

      it('should call onError when websocket server emits connect_error', async () => {
        const loggerSpy = jest.spyOn(logger, 'debug');
        const onSuccessMock = jest.fn();
        const onErrorMock = jest.fn();
        Cookies.get = jest.fn().mockImplementationOnce(() => 'mockAuthToken');

        await agentAssistUtils.getWebsocketStatus('mockNotifierServerEndpoint', onSuccessMock, onErrorMock);
        mockSocket.on.mock.calls[0][1]({ message: 'xhr poll error' });

        expect(onErrorMock).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledTimes(1);
        expect(loggerSpy).toBeCalledWith('[Agent-Assist] connect_error due to xhr poll error');
      });
    });
  });

  describe('Utility functions', () => {
    let agentAssistUtils;

    beforeAll(() => {
      agentAssistUtils = AgentAssistUtils.instance;
    });

    it('should return a conversation name when conversation id is passed', () => {
      const conversationName = agentAssistUtils.getConversationName('mockConversationId');
      expect(conversationName).toBe('projects/mockGcpProject/locations/mockLocation/conversations/mockConversationId');
    });
  });
});
