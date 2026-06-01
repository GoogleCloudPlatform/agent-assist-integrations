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

const componentHooks = [] as any[];

export const init = (flex: typeof Flex, manager: Flex.Manager) => {
  for (const hook of componentHooks) {
    hook.componentHook(flex, manager);
  }
};

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  console.info(
    `Feature ${feature} registered %c${hook.componentName} %ccomponent hook: %c${hook.componentHook.name}`,
    'font-weight:bold',
    'font-weight:normal',
    'font-weight:bold',
  );
  componentHooks.push(hook);
};
