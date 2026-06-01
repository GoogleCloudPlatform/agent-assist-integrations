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

import { FlexActionEvent, FlexAction } from '../../../../types/feature-loader';
import AgentAssistUtils from '../../utils/agentAssist/AgentAssistUtils';
import { isVoiceEnabled, getConversationProfile, getCustomApiEndpoint, getNotifierServerEndpoint } from '../../config';
import { updateAgentAssistState } from '../states/AgentAssist';
import logger from '../../../../utils/logger';

export const actionEvent = FlexActionEvent.after;
export const actionName = FlexAction.SetActivity;
export const actionHook = function afterSetActivity(flex: typeof Flex, _manager: Flex.Manager) {
  flex.Actions.addListener(`${actionEvent}${actionName}`, async (payload, abortFunction) => {
    console.log('this fires on refresh');
    const { activityName } = payload;
    const agentAssistUtils = AgentAssistUtils.instance;
    switch (activityName) {
      case 'Available':
        loginFlow(agentAssistUtils, _manager);
        break;
      case 'Break':
      case 'Offline':
      case 'Unavailable':
        Cookies.remove('CCAI_AGENT_ASSIST_AUTH_TOKEN');
        _manager.store.dispatch(
          updateAgentAssistState({
            status: 'disconnected',
            authToken: '',
          }),
        );
        break;
    }
  });
};

const loginFlow = async (agentAssistUtils: AgentAssistUtils, manager: Flex.Manager) => {
  logger.debug('[Agent-Assist] Initialzing UI Modules');
  const agentToken = manager.store.getState().flex.session.ssoTokenPayload.token;
  const authToken = await agentAssistUtils.getAgentAssistAuthToken(agentToken);
  const connectorConfig = {
    channel: isVoiceEnabled() ? 'voice' : 'chat',
    agentDesktop: 'Custom',
    agentDesktopSource: 'TWILIO',
    conversationProfileName: getConversationProfile(),
    apiConfig: {
      authToken,
      customApiEndpoint: getCustomApiEndpoint(),
    },
    eventBasedConfig: {
      transport: 'websocket',
      library: 'SocketIo',
      notifierServerEndpoint: getNotifierServerEndpoint(),
    },
    UiModuleEventOptions: {
      namespace: 'twilio',
    },
  };
  agentAssistUtils.initializeUiConnector(connectorConfig);
  manager.store.dispatch(
    updateAgentAssistState({
      status: 'connected',
      authToken,
    }),
  );
};
