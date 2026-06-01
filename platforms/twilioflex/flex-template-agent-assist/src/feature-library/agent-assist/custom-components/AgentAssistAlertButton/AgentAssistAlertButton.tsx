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

import React, { useEffect } from 'react';
import { Flex as PasteFlexComponent } from '@twilio-paste/core/flex';
import { IconButton, templates } from '@twilio/flex-ui';
import * as Flex from '@twilio/flex-ui';
import { useDispatch, useSelector } from 'react-redux';
import { Tooltip } from '@twilio-paste/core/tooltip';

import { AgentAssistIcon } from '../../flex-hooks/icons/AgentAssistIcon.jsx';
import { AppState } from '../../../../types/manager';
import { reduxNamespace } from '../../../../utils/state';
import { AgentAssistState } from '../../flex-hooks/states/AgentAssist';
import AgentAssistUtils from '../../utils/agentAssist/AgentAssistUtils';
import { isVoiceEnabled, getConversationProfile, getCustomApiEndpoint, getNotifierServerEndpoint } from '../../config';
import { updateAgentAssistState } from '../../flex-hooks/states/AgentAssist';
import { StringTemplates } from '../../flex-hooks/strings/AgentAssist';
import logger from '../../../../utils/logger';

export const AgentAssistAlertButton = () => {
  const dispatch = useDispatch();

  const { status } = useSelector((state: AppState) => state[reduxNamespace].agentAssist as AgentAssistState);
  const manager = Flex.Manager.getInstance();
  const agentToken = manager.user.token;
  const isAvailable = useSelector((state: AppState) => state.flex.worker.activity.available);

  useEffect(() => {
    const agentAssistUtils = AgentAssistUtils.instance;
    const connectorConfig = {
      channel: isVoiceEnabled() ? 'voice' : 'chat',
      agentDesktop: 'Custom',
      conversationProfileName: getConversationProfile(),
      apiConfig: {
        authToken: '',
        customApiEndpoint: getCustomApiEndpoint(),
      },
      eventBasedConfig: {
        transport: 'websocket',
        library: 'SocketIo',
        notifierServerEndpoint: getNotifierServerEndpoint(),
      },
    };
    const fetchAuthToken = async () => {
      return agentAssistUtils.getAgentAssistAuthToken(agentToken);
    };
    const refreshAuthToken = async () => {
      const authToken = await agentAssistUtils.getAgentAssistAuthToken(agentToken);
      agentAssistUtils.setAgentAssistAuthToken(authToken);
    };
    if (isAvailable) {
      logger.info('[Agent-Assist] Agent marked as available on page load. Setting up UI Modules');
      fetchAuthToken().then((authToken) => {
        connectorConfig.apiConfig.authToken = authToken;
        agentAssistUtils.initializeUiConnector(connectorConfig);
        dispatch(
          updateAgentAssistState({
            status: 'connected',
            authToken,
          }),
        );
      });
      setTimeout(refreshAuthToken, 3600 * 1000);
    }
  }, []);

  return (
    <PasteFlexComponent vAlignContent="center">
      <Tooltip
        text={
          status === 'connected'
            ? templates[StringTemplates.AgentAssistConnected]()
            : templates[StringTemplates.AgentAssistDisconnected]()
        }
        placement="left"
      >
        <IconButton
          title="agent-assist-icon"
          disabled={status !== 'connected'}
          icon={<AgentAssistIcon />}
          size="small"
          style={{ backgroundColor: 'transparent' }}
        />
      </Tooltip>
    </PasteFlexComponent>
  );
};
