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

import axe from '../../../../../../test-utils/axe-helper';
import { AgentAssistAdminGeneralSettings } from './AgentAssistAdminGeneralSettings';
import {
  setServiceConfiguration,
  getMockedServiceConfiguration,
} from '../../../../../../test-utils/flex-service-configuration';
import { StringTemplates as AdminUiStringTemplates } from '../../../flex-hooks/strings/AgentAssistAdmin';
import AgentAssistUtils from '../../../utils/agentAssist/AgentAssistUtils';
import { renderWithProviders } from '../../../../../../test-utils/test-utils';

describe('AgentAssistAdminGeneralSettings', () => {
  describe('When the form is empty', () => {
    it('should display place holder text for the custom api input box', async () => {
      const placeholderText = 'Enter custom api endpoint';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const input = await screen.findByPlaceholderText(placeholderText);

      expect(input).toBeDefined();
    });

    it('should have placeholder text for conversation profile input', async () => {
      const placeholderText = 'Enter conversation profile id';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const input = await screen.findByPlaceholderText(placeholderText);

      expect(input).toBeDefined();
    });

    it('should have test button disabled when conversationProfile and customeApiEndpoint are empty', async () => {
      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');

      expect(button).toHaveProperty('disabled', true);
    });
  });

  describe('when filling out configuration values', () => {
    it('should not enable test button if only custom api endpoint is filled', async () => {
      const customApiEndpoint = 'https://8.8.8.8';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const input = await screen.findByTestId('custom-api-endpoint-input');
      await userEvent.type(input, customApiEndpoint);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');

      expect(button).toHaveProperty('disabled', true);
    });

    it('should not enable test button if only conversation profile is filled', async () => {
      const conversationProfile = 'mockConversationProfile';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const input = await screen.findByTestId('conversation-profile-input');
      await userEvent.type(input, conversationProfile);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');

      expect(button).toHaveProperty('disabled', true);
    });

    it('should enable test button if both conversation profile and custom api endpoint are filled', async () => {
      const conversationProfile = 'mockConversationProfile';
      const customApiEndpoint = 'https://8.8.8.8';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const customApiEndpointInput = await screen.findByTestId('custom-api-endpoint-input');
      await userEvent.type(customApiEndpointInput, customApiEndpoint);

      const conversationProfileInput = await screen.findByTestId('conversation-profile-input');
      await userEvent.type(conversationProfileInput, conversationProfile);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');

      expect(button).toHaveProperty('disabled', false);
    });
  });

  describe('When validating the agent assist config', () => {
    beforeEach(async () => {
      const conversationProfile = 'mockConversationProfile';
      const customApiEndpoint = 'https://8.8.8.8';

      renderWithProviders(<AgentAssistAdminGeneralSettings />);

      const customApiEndpointInput = await screen.findByTestId('custom-api-endpoint-input');
      await userEvent.type(customApiEndpointInput, customApiEndpoint);

      const conversationProfileInput = await screen.findByTestId('conversation-profile-input');
      await userEvent.type(conversationProfileInput, conversationProfile);
    });

    it('should provide an error message when there is an issue with the custom api endpoint', async () => {
      const agentAssistUtils = AgentAssistUtils.instance;
      agentAssistUtils.getAgentAssistAuthToken = jest.fn().mockImplementationOnce(() => 'mockAuthToken');
      agentAssistUtils.getStatus = jest.fn().mockImplementationOnce(() => false);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');
      await userEvent.click(button);

      const errorMessage = await screen.findByText(AdminUiStringTemplates.ConnectingToCustomApiEndpointError);

      expect(errorMessage).toBeDefined();
    });

    it('should provide an error message when there is an issue with the conversation profile', async () => {
      const agentAssistUtils = AgentAssistUtils.instance;
      agentAssistUtils.getAgentAssistAuthToken = jest.fn().mockImplementationOnce(() => 'mockAuthToken');
      agentAssistUtils.getStatus = jest.fn().mockImplementationOnce(() => true);
      agentAssistUtils.getConversationProfile = jest.fn().mockImplementationOnce(() => undefined);

      const button = await screen.findByTestId('validate-agent-assist-config-btn');
      await userEvent.click(button);

      const errorMessage = await screen.findByText(AdminUiStringTemplates.ValidateConversationProfileError);

      expect(errorMessage).toBeDefined();
    });

    it('should provide an success message when the provide config is valid', async () => {
      const agentAssistUtils = AgentAssistUtils.instance;
      agentAssistUtils.getAgentAssistAuthToken = jest.fn().mockImplementationOnce(() => 'mockAuthToken');
      agentAssistUtils.getStatus = jest.fn().mockImplementationOnce(() => true);
      agentAssistUtils.getConversationProfile = jest.fn().mockImplementationOnce(() => 'mockConversationProfile');

      const button = await screen.findByTestId('validate-agent-assist-config-btn');
      await userEvent.click(button);

      const errorMessage = await screen.findByText(AdminUiStringTemplates.ValidateConfigSuccess);

      expect(errorMessage).toBeDefined();
    });
  });

  it('should pass accessibility test', async () => {
    const { container } = renderWithProviders(<AgentAssistAdminGeneralSettings />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
