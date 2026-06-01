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

// @ts-nocheck
import * as Flex from '@twilio/flex-ui';

import { AgentAssistEvent } from '../../types/feature-loader';

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  if (!hook.agentAssistEventName) {
    console.info(`Feature ${feature} declared agent assist event hook, but is missing agentAssistEventName to hook`);
    return;
  }
  const event = hook.agentAssistEventName as AgentAssistEvent;

  console.info(
    `Feature ${feature} registered %c${event} %cevent hook: %c${hook.agentAssistEventHook.name}`,
    'font-weight:bold',
    'font-weight:normal',
    'font-weight:bold',
  );

  addAgentAssistEventListener(event, function (eventPayload: any) {
    hook.agentAssistEventHook(flex, manager, eventPayload);
  });
};
