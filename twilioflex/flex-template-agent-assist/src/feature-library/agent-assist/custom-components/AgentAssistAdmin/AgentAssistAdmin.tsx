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

import React, { useEffect, useState } from 'react';
import { FormControl, FormSection, FormSectionHeading } from '@twilio-paste/core/form';
import { Switch } from '@twilio-paste/core/switch';
import { Separator } from '@twilio-paste/core/separator';
import { templates } from '@twilio/flex-ui';
import { useDispatch, useSelector } from 'react-redux';

import { StringTemplates as AgentAssistStringTemplates } from '../../flex-hooks/strings/AgentAssist';
import { AgentAssistAdminVoiceSettings } from './AgentAssistAdminVoiceSettings';
import { AgentAssistAdminFeatureSettings } from './AgentAssistAdminFeatureSettings';
import { AgentAssistAdminGeneralSettings } from './AgentAssistAdminGeneralSettings';
import { AppState } from '../../../../types/manager';
import { reduxNamespace } from '../../../../utils/state';
import { AgentAssistAdminState, updateAgentAssistAdminState } from '../../flex-hooks/states/AgentAssistAdmin';

interface OwnProps {
  feature: string;
  initialConfig: any;
  setModifiedConfig: (featureName: string, newConfig: any) => void;
  setAllowSave: (featureName: string, allowSave: boolean) => void;
}

export const AgentAssistAdmin = (props: OwnProps) => {
  const dispatch = useDispatch();
  const agentAssistAdminState = useSelector(
    (state: AppState) => state[reduxNamespace].agentAssistAdmin as AgentAssistAdminState,
  );

  const setAllowSave = (allowSave: boolean) => {
    props.setAllowSave(props.feature, allowSave);
  };

  useEffect(() => {
    dispatch(updateAgentAssistAdminState({ ...props.initialConfig }));
  }, []);

  useEffect(() => {
    const { hasError, ...rest } = agentAssistAdminState;
    setAllowSave(!hasError);
    props.setModifiedConfig(props.feature, {
      ...rest,
    });
  }, [agentAssistAdminState]);

  return (
    <>
      <AgentAssistAdminGeneralSettings />
      <Separator orientation="horizontal" />
      <AgentAssistAdminFeatureSettings />
      <Separator orientation="horizontal" />
      <AgentAssistAdminVoiceSettings />
      <Separator orientation="horizontal" />
      <FormSection>
        <FormSectionHeading>Troubleshooting</FormSectionHeading>
        <FormControl key={'debug-control'}>
          <Switch
            checked={agentAssistAdminState.debug}
            onChange={(e) => dispatch(updateAgentAssistAdminState({ debug: e.target.checked }))}
          >
            {templates[AgentAssistStringTemplates.Debug]()}
          </Switch>
        </FormControl>
      </FormSection>
    </>
  );
};
