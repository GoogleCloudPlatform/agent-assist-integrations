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

import { FlexActionEvent } from '../../../../types/feature-loader';
import { StringTemplates } from '../strings/AgentAssist';
import { AgentAssistContainer } from '../../custom-components/AgentAssistContainer/AgentAssistContainer';

export const actionEvent = FlexActionEvent.before;
export const actionName = 'LoadCRMContainerTabs';
export const actionHook = function addAgentAssistContainerToEnhancedCRM(flex: typeof Flex, manager: Flex.Manager) {
  flex.Actions.addListener(`${actionEvent}${actionName}`, async (payload) => {
    if (!payload.task || Flex.TaskHelper.isInWrapupMode(payload.task)) {
      return;
    }

    payload.components = [
      ...payload.components,
      {
        title: (manager.strings as any)[StringTemplates.AgentAssist],
        order: 0,
        component: <AgentAssistContainer />,
      },
    ];
  });
};
