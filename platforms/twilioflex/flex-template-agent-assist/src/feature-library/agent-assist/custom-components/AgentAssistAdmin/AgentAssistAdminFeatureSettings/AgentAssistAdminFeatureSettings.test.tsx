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

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as Flex from '@twilio/flex-ui';

import { AgentAssistAdminFeatureSettings } from './AgentAssistAdminFeatureSettings';
import axe from '../../../../../../test-utils/axe-helper';
import {
  setServiceConfiguration,
  getMockedServiceConfiguration,
} from '../../../../../../test-utils/flex-service-configuration';
import { StringTemplates as AgentAssistStringTemplates } from '../../../flex-hooks/strings/AgentAssist';
import defaultConfigurationValues from '../../../../../../../flex-config/ui_attributes.common.json';
import { renderWithProviders } from '../../../../../../test-utils/test-utils';

describe('AgentAssistAdminFeatureSettings', () => {
  describe.skip('When configuration values are stored in the configuration service', () => {
    it('should display the saved value for agent coaching', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { agent_coaching } = custom_data.features.agent_assist;

      render(<AgentAssistAdminFeatureSettings />);

      const agentCoachingSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.AgentCoaching}-switch`,
      );

      expect(agentCoachingSwitch).toHaveProperty('checked', agent_coaching);
    });

    it('should display the saved value for conversation summary', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { conversation_summary } = custom_data.features.agent_assist;

      render(<AgentAssistAdminFeatureSettings />);

      const conversationSummarySwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.ConversationSummarization}-switch`,
      );

      expect(conversationSummarySwitch).toHaveProperty('checked', conversation_summary);
    });

    it('should display the saved value for smart reply', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { smart_reply } = custom_data.features.agent_assist;

      render(<AgentAssistAdminFeatureSettings />);

      const smartReplySwitch = await screen.findByTestId(`enable-${AgentAssistStringTemplates.SmartReply}-switch`);

      expect(smartReplySwitch).toHaveProperty('checked', smart_reply);
    });

    it('should display the saved value for knowleadge assist', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { knowledge_assist } = custom_data.features.agent_assist;

      render(<AgentAssistAdminFeatureSettings />);

      const knowleadgeAssistSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.KnowledgeAssist}-switch`,
      );

      expect(knowleadgeAssistSwitch).toHaveProperty('checked', knowledge_assist);
    });
  });

  describe.skip('When no configuation values are stored in the configation server', () => {
    beforeEach(async () => {
      setServiceConfiguration({ ui_attributes: { ...defaultConfigurationValues } }, null);
    });

    it('should display the default value for agent coaching', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { agent_coaching } = custom_data.features.agent_assist;

      renderWithProviders(<AgentAssistAdminFeatureSettings />);

      const agentCoachingSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.AgentCoaching}-switch`,
      );

      expect(agentCoachingSwitch).toHaveProperty('checked', agent_coaching);
    });

    it('should display the default value for conversation summary', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { conversation_summary } = custom_data.features.agent_assist;

      renderWithProviders(<AgentAssistAdminFeatureSettings />);

      const conversationSummarySwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.ConversationSummarization}-switch`,
      );

      expect(conversationSummarySwitch).toHaveProperty('checked', conversation_summary);
    });

    it('should display the default value for smart reply', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { smart_reply } = custom_data.features.agent_assist;

      renderWithProviders(<AgentAssistAdminFeatureSettings />);

      const smartReplySwitch = await screen.findByTestId(`enable-${AgentAssistStringTemplates.SmartReply}-switch`);

      expect(smartReplySwitch).toHaveProperty('checked', smart_reply);
    });

    it('should display the default value for knowleadge assist', async () => {
      const { custom_data } = Flex.Manager.getInstance().configuration;
      const { knowledge_assist } = custom_data.features.agent_assist;

      renderWithProviders(<AgentAssistAdminFeatureSettings />);

      const knowleadgeAssistSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.KnowledgeAssist}-switch`,
      );

      expect(knowleadgeAssistSwitch).toHaveProperty('checked', knowledge_assist);
    });
  });

  describe('When the user edits values in admin panel', () => {
    beforeEach(() => {
      renderWithProviders(<AgentAssistAdminFeatureSettings />);
    });

    it('should be able to toggle agent coaching', async () => {
      const agentCoachingSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.AgentCoaching}-switch`,
      );
      await userEvent.click(agentCoachingSwitch);

      expect(agentCoachingSwitch).toHaveProperty('checked', false);
    });

    it('should be able to toggle conversation summary', async () => {
      const conversationSummarySwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.ConversationSummarization}-switch`,
      );
      await userEvent.click(conversationSummarySwitch);

      expect(conversationSummarySwitch).toHaveProperty('checked', false);
    });

    it('should be able to toggle smart reply', async () => {
      const smartReplySwitch = await screen.findByTestId(`enable-${AgentAssistStringTemplates.SmartReply}-switch`);
      await userEvent.click(smartReplySwitch);

      expect(smartReplySwitch).toHaveProperty('checked', false);
    });

    it('should be able to toggle knowleadge assist', async () => {
      const knowleadgeAssistSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.KnowledgeAssist}-switch`,
      );
      await userEvent.click(knowleadgeAssistSwitch);

      expect(knowleadgeAssistSwitch).toHaveProperty('checked', false);
    });
  });

  it('should pass accessibility test', async () => {
    const { container } = render(<AgentAssistAdminFeatureSettings />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
