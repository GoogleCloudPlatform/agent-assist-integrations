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
import { Switch, SwitchGroup } from '@twilio-paste/core/switch';
import { useDispatch, useSelector } from 'react-redux';

import { StringTemplates as AgentAssistStringTemplates } from '../../../flex-hooks/strings/AgentAssist';
import { StringTemplates as AdminUiStringTemplates } from '../../../flex-hooks/strings/AgentAssistAdmin';
import { AppState } from '../../../../../types/manager';
import { reduxNamespace } from '../../../../../utils/state';
import { AgentAssistAdminState, updateAgentAssistAdminState } from '../../../flex-hooks/states/AgentAssistAdmin';

export const AgentAssistAdminFeatureSettings = () => {
  const dispatch = useDispatch();
  const { agent_coaching, conversation_summary, smart_reply, knowledge_assist } = useSelector(
    (state: AppState) => state[reduxNamespace].agentAssistAdmin as AgentAssistAdminState,
  );

  const agentAssistFeatures = [
    {
      checked: agent_coaching,
      onChange: (e: any) => dispatch(updateAgentAssistAdminState({ agent_coaching: e.target.checked })),
      helpText: templates[AdminUiStringTemplates.AgentCoachingHelperText](),
      label: templates[AgentAssistStringTemplates.AgentCoaching](),
    },
    {
      checked: conversation_summary,
      onChange: (e: any) => dispatch(updateAgentAssistAdminState({ conversation_summary: e.target.checked })),
      helpText: templates[AdminUiStringTemplates.ConversationSummarizationHelperText](),
      label: templates[AgentAssistStringTemplates.ConversationSummarization](),
    },
    {
      checked: smart_reply,
      onChange: (e: any) => dispatch(updateAgentAssistAdminState({ smart_reply: e.target.checked })),
      helpText: templates[AdminUiStringTemplates.SmartReplyHelperText](),
      label: templates[AgentAssistStringTemplates.SmartReply](),
    },
    {
      checked: knowledge_assist,
      onChange: (e: any) => dispatch(updateAgentAssistAdminState({ knowledge_assist: e.target.checked })),
      helpText: templates[AdminUiStringTemplates.KnowledgeAssistHelperText](),
      label: templates[AgentAssistStringTemplates.KnowledgeAssist](),
    },
  ];

  return (
    <FormSection>
      <FormSectionHeading>Agent Assist Features</FormSectionHeading>
      <FormControl key={'agent-assist-feature-control'}>
        <SwitchGroup name="agent-assist-features" legend={<></>}>
          {agentAssistFeatures.map((feature) => {
            const { label, ...props } = feature;
            return (
              <Switch data-testid={`enable-${label}-switch`} {...props}>
                {label}
              </Switch>
            );
          })}
        </SwitchGroup>
      </FormControl>
    </FormSection>
  );
};
