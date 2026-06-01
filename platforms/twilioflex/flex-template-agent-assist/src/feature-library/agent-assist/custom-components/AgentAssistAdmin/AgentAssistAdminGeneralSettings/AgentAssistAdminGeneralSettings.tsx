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

import { templates } from '@twilio/flex-ui';
import { FormControl, FormSection, FormSectionHeading } from '@twilio-paste/core/form';
import { Stack } from '@twilio-paste/core/stack';
import { Label } from '@twilio-paste/core/label';
import { Input } from '@twilio-paste/core/input';
import { HelpText } from '@twilio-paste/core/help-text';
import { useEffect, useState } from 'react';
import * as Flex from '@twilio/flex-ui';
import { useDispatch, useSelector } from 'react-redux';
import { Button } from '@twilio-paste/core/button';

import { AppState } from '../../../../../types/manager';
import { reduxNamespace } from '../../../../../utils/state';
import { AgentAssistAdminState, updateAgentAssistAdminState } from '../../../flex-hooks/states/AgentAssistAdmin';
import { StringTemplates as AgentAssistStringTemplates } from '../../../flex-hooks/strings/AgentAssist';
import { StringTemplates as AdminUiStringTemplates } from '../../../flex-hooks/strings/AgentAssistAdmin';
import AgentAssistUtils from '../../../utils/agentAssist/AgentAssistUtils';

interface StatusMessage {
  message: string;
  type: 'success' | 'error';
}

export const AgentAssistAdminGeneralSettings = () => {
  const dispatch = useDispatch();
  const { conversation_profile, custom_api_endpoint, hasError } = useSelector(
    (state: AppState) => state[reduxNamespace].agentAssistAdmin as AgentAssistAdminState,
  );
  const [statusMessage, setStatusMessage] = useState<StatusMessage>();

  const manager = Flex.Manager.getInstance();
  const agentToken = manager.user.token;
  const agentAssistUtils = AgentAssistUtils.instance;

  useEffect(() => {
    dispatch(updateAgentAssistAdminState({ hasError: statusMessage?.type === 'error' }));
  }, [statusMessage]);

  const isBlank = (str: string): boolean => {
    return !str || /^\s*$/.test(str);
  };

  const validateCustomApiEndpoint = async (customApiEndpoint: string) => {
    try {
      await agentAssistUtils.getAgentAssistAuthToken(agentToken, customApiEndpoint);
      const isValid = await agentAssistUtils.getStatus(customApiEndpoint);
      if (!isValid) {
        throw new Error(templates[AdminUiStringTemplates.ConnectingToCustomApiEndpointError]());
      }
    } catch (error) {
      throw new Error(templates[AdminUiStringTemplates.ConnectingToCustomApiEndpointError]());
    }
  };

  const validateConversationProfileExists = async (conversationProfile: string, customApiEndpoint: string) => {
    try {
      await agentAssistUtils.getAgentAssistAuthToken(agentToken, customApiEndpoint);
      const conversationProfileName = await agentAssistUtils.getConversationProfile(
        conversationProfile,
        customApiEndpoint,
      );
      if (!conversationProfileName) {
        throw new Error(templates[AdminUiStringTemplates.ValidateConversationProfileError]());
      }
    } catch (error) {
      throw new Error(templates[AdminUiStringTemplates.ValidateConversationProfileError]());
    }
  };

  const validateAgentAssistConfiguration = async (conversationProfile: string, customApiEndpoint: string) => {
    try {
      await validateCustomApiEndpoint(customApiEndpoint);
      await validateConversationProfileExists(conversationProfile, customApiEndpoint);
      setStatusMessage({
        type: 'success',
        message: templates[AdminUiStringTemplates.ValidateConfigSuccess](),
      });
    } catch (error) {
      if (error instanceof Error) {
        setStatusMessage({ type: 'error', message: error.message });
      }
    }
  };

  return (
    <FormSection>
      <FormSectionHeading>General Settings</FormSectionHeading>
      <FormControl key={'custom-api-endpoint-control'}>
        <Stack orientation="vertical" spacing="space60">
          <Label htmlFor={'custom-api-endpoint'}>{templates[AgentAssistStringTemplates.CustomApiEndpoint]()}</Label>
          <Input
            data-testid="custom-api-endpoint-input"
            id={'custom-api-endpoint'}
            name={'custom-api-endpoint'}
            type="text"
            value={custom_api_endpoint}
            placeholder="Enter custom api endpoint"
            onChange={(e) => dispatch(updateAgentAssistAdminState({ custom_api_endpoint: e.target.value }))}
          />
        </Stack>
      </FormControl>
      <FormControl key={'conversation-profile-control'}>
        <Stack orientation="vertical" spacing="space60">
          <>
            <Label htmlFor={'conversation-profile'}>
              {templates[AgentAssistStringTemplates.ConversationProfile]()}
            </Label>
            <Input
              data-testid="conversation-profile-input"
              id={'conversation-profile'}
              name={'conversation-profile'}
              type="text"
              value={conversation_profile}
              onChange={(e) => dispatch(updateAgentAssistAdminState({ conversation_profile: e.target.value }))}
              placeholder="Enter conversation profile id"
            />
          </>
          <Stack orientation="horizontal" spacing="space30">
            <Button
              variant="primary"
              onClick={async () => validateAgentAssistConfiguration(conversation_profile, custom_api_endpoint)}
              data-testid={'validate-agent-assist-config-btn'}
              disabled={isBlank(conversation_profile) || isBlank(custom_api_endpoint)}
            >
              {templates[AdminUiStringTemplates.TestConnectionCTA]()}
            </Button>
            {statusMessage && (
              <HelpText id="endpoint-help-text" variant={statusMessage.type}>
                {statusMessage.message}
              </HelpText>
            )}
          </Stack>
        </Stack>
      </FormControl>
    </FormSection>
  );
};
