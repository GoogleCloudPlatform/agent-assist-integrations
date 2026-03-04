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

import { FormControl, FormSection, FormSectionHeading } from '@twilio-paste/core/form';
import { Stack } from '@twilio-paste/core/stack';
import { Label } from '@twilio-paste/core/label';
import { Input } from '@twilio-paste/core/input';
import { templates } from '@twilio/flex-ui';
import { Switch } from '@twilio-paste/core/switch';
import { useEffect, useState } from 'react';
import * as Flex from '@twilio/flex-ui';
import { useDispatch, useSelector } from 'react-redux';
import { Button } from '@twilio-paste/core/button';
import { HelpText } from '@twilio-paste/core/help-text';

import { SwitchWithOptions } from '../AgentAssistAdminComponents';
import { StringTemplates as AdminUiStringTemplates } from '../../../flex-hooks/strings/AgentAssistAdmin';
import { StringTemplates as AgentAssistStringTemplates } from '../../../flex-hooks/strings/AgentAssist';
import AgentAssistUtils from '../../../utils/agentAssist/AgentAssistUtils';
import { AppState } from '../../../../../types/manager';
import { reduxNamespace } from '../../../../../utils/state';
import { AgentAssistAdminState, updateAgentAssistAdminState } from '../../../flex-hooks/states/AgentAssistAdmin';

interface StatusMessage {
  message: string;
  type: 'success' | 'error';
}

export const AgentAssistAdminVoiceSettings = () => {
  const dispatch = useDispatch();
  const { enable_voice, transcription, notifier_server_endpoint } = useSelector(
    (state: AppState) => state[reduxNamespace].agentAssistAdmin as AgentAssistAdminState,
  );
  const [statusMessage, setStatusMessage] = useState<StatusMessage>();

  useEffect(() => {
    dispatch(updateAgentAssistAdminState({ hasError: statusMessage?.type === 'error' }));
  }, [statusMessage]);

  const manager = Flex.Manager.getInstance();
  const agentToken = manager.user.token;
  const agentAssistUtils = AgentAssistUtils.instance;

  const transcriptionOptions = [
    {
      value: templates[AgentAssistStringTemplates.LiveTranscription](),
      helpText: templates[AdminUiStringTemplates.LiveTranscriptionHelperText](),
      label: templates[AgentAssistStringTemplates.LiveTranscription](),
      defaultChecked: true,
    },
    {
      value: templates[AgentAssistStringTemplates.IntermediateTranscription](),
      helpText: templates[AdminUiStringTemplates.IntermediateTranscriptionHelperText](),
      label: templates[AgentAssistStringTemplates.IntermediateTranscription](),
    },
  ];

  const isBlank = (str: string): boolean => {
    return !str || /^\s*$/.test(str);
  };

  const validateNotifierServerEndpoint = async (notifierServerEndpoint: string) => {
    const onSuccess = () =>
      setStatusMessage({
        type: 'success',
        message: templates[AdminUiStringTemplates.ConnectingToCustomApiEndpointSuccess](),
      });
    const onError = () =>
      setStatusMessage({
        type: 'error',
        message: templates[AdminUiStringTemplates.ConnectingToNotifierServerEndpointError](),
      });
    try {
      await agentAssistUtils.getAgentAssistAuthToken(agentToken, notifierServerEndpoint);
      agentAssistUtils.getWebsocketStatus(notifierServerEndpoint, onSuccess, onError);
    } catch (error) {}
  };

  const transcriptionVersionHandler = (version: string) => {
    switch (version) {
      case templates[AgentAssistStringTemplates.LiveTranscription]():
        dispatch(
          updateAgentAssistAdminState({
            transcription: {
              ...transcription,
              version: {
                live_transcription: true,
                intermediate_transcription: false,
              },
            },
          }),
        );
        break;
      case templates[AgentAssistStringTemplates.IntermediateTranscription]():
      default:
        dispatch(
          updateAgentAssistAdminState({
            transcription: {
              ...transcription,
              version: {
                live_transcription: false,
                intermediate_transcription: true,
              },
            },
          }),
        );
        break;
    }
  };
  return (
    <FormSection>
      <FormSectionHeading>Voice Settings</FormSectionHeading>
      <FormControl key={'voice-control'}>
        <Switch
          data-testid={'enable-voice-switch'}
          checked={enable_voice}
          onChange={(e) => dispatch(updateAgentAssistAdminState({ enable_voice: e.target.checked }))}
        >
          Enable Voice
        </Switch>
      </FormControl>
      <FormControl key={'notifier-server-endpoint-control'}>
        <Stack orientation="vertical" spacing="space60">
          <>
            <Label htmlFor={'notifier-server-endpoint'}>
              {templates[AgentAssistStringTemplates.NotiferServerEnpoint]()}
            </Label>
            <Input
              id={'notifier-server-endpoint'}
              data-testid="notifier-server-endpoint-input"
              name={'notifier-server-endpoint'}
              type="text"
              value={notifier_server_endpoint}
              onChange={(e) => dispatch(updateAgentAssistAdminState({ notifier_server_endpoint: e.target.value }))}
              placeholder="Enter notifier server endpoint"
              disabled={!enable_voice}
            />
          </>
          <Stack orientation="horizontal" spacing="space30">
            <Button
              variant="primary"
              onClick={async () => validateNotifierServerEndpoint(notifier_server_endpoint)}
              data-testid={'validate-notifier-server-endpoint-btn'}
              disabled={isBlank(notifier_server_endpoint)}
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
      <FormControl key={'transcription-control'}>
        <SwitchWithOptions
          isEnabled={transcription.enabled}
          featureChangeHandler={(e: any) =>
            dispatch(
              updateAgentAssistAdminState({
                transcription: {
                  ...transcription,
                  enabled: !transcription.enabled,
                },
              }),
            )
          }
          featureOptions={transcriptionOptions}
          featureDisabled={!enable_voice}
          featureLabel={templates[AgentAssistStringTemplates.Transcription]()}
          optionsChangeHandler={transcriptionVersionHandler}
          optionsDisabled={!(transcription.enabled && enable_voice)}
        />
      </FormControl>
    </FormSection>
  );
};
