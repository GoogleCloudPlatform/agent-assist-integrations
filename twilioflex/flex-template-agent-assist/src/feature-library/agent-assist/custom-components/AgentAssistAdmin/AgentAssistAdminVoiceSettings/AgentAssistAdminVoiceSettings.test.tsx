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

import { screen } from '@testing-library/react';

import { AgentAssistAdminVoiceSettings } from './AgentAssistAdminVoiceSettings';
import axe from '../../../../../../test-utils/axe-helper';
import { StringTemplates as AgentAssistStringTemplates } from '../../../flex-hooks/strings/AgentAssist';
import { renderWithProviders } from '../../../../../../test-utils/test-utils';

describe('AgentAssistAdminVoiceSettings', () => {
  describe('When the form is empty', () => {
    it('should display place holder text for the notifier server endpoint input box', async () => {
      const placeholderText = 'Enter notifier server endpoint';

      renderWithProviders(<AgentAssistAdminVoiceSettings />);

      const input = await screen.findByPlaceholderText(placeholderText);

      expect(input).toBeDefined();
    });

    it('should have enable audio off by default', async () => {
      renderWithProviders(<AgentAssistAdminVoiceSettings />);

      const enableVoiceSwitch = await screen.findByTestId(`enable-voice-switch`);

      expect(enableVoiceSwitch).toHaveProperty('checked', false);
    });

    it('should have enable transcription off by default', async () => {
      renderWithProviders(<AgentAssistAdminVoiceSettings />);

      const enableTranscriptionSwitch = await screen.findByTestId(
        `enable-${AgentAssistStringTemplates.Transcription}-switch`,
      );

      expect(enableTranscriptionSwitch).toHaveProperty('checked', false);
    });
  });

  it('should pass accessibility test', async () => {
    const { container } = renderWithProviders(<AgentAssistAdminVoiceSettings />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
