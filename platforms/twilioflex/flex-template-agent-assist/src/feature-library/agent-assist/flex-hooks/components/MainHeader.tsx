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

import { isAgentAssistEnabled } from '../../utils/helpers';
import { FlexComponent } from '../../../../types/feature-loader';
import AgentAssistAlertButton from '../../custom-components/AgentAssistAlertButton';

export const componentName = FlexComponent.MainHeader;
export const componentHook = function addAgentAssistToMainHeader(flex: typeof Flex, manager: Flex.Manager) {
  if (!isAgentAssistEnabled()) {
    return;
  }

  // Add alert button to the main header
  flex.MainHeader.Content.add(<AgentAssistAlertButton key="template-agent-assist-main-header" />, {
    sortOrder: -1,
    align: 'end',
  });
};
