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

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  if (!hook.eventName) {
    console.info(`Feature ${feature} declared notification event hook, but is missing eventName to hook`);
    return;
  }
  const event = hook.eventName as Flex.NotificationEvent;

  console.info(
    `Feature ${feature} registered %c${event} %cnotification event hook: %c${hook.notificationEventHook.name}`,
    'font-weight:bold',
    'font-weight:normal',
    'font-weight:bold',
  );

  flex.Notifications.addListener(event, (notification, cancel) => {
    hook.notificationEventHook(flex, manager, notification, cancel);
  });
};
