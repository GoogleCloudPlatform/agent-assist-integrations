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

import { FlexEvent } from '../../types/feature-loader';
import Activity from '../../types/task-router/Activity';

const taskEvents = [
  FlexEvent.taskAccepted,
  FlexEvent.taskCanceled,
  FlexEvent.taskCompleted,
  FlexEvent.taskReceived,
  FlexEvent.taskRejected,
  FlexEvent.taskRescinded,
  FlexEvent.taskTimeout,
  FlexEvent.taskUpdated,
  FlexEvent.taskWrapup,
];

const isTaskEvent = (event: FlexEvent): boolean => {
  return taskEvents.includes(event);
};

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  if (!hook.eventName) {
    console.info(`Feature ${feature} declared event hook, but is missing eventName to hook`);
    return;
  }
  const event = hook.eventName as FlexEvent;

  console.info(
    `Feature ${feature} registered %c${event} %cevent hook: %c${hook.eventHook.name}`,
    'font-weight:bold',
    'font-weight:normal',
    'font-weight:bold',
  );

  if (event === FlexEvent.pluginsInitialized) {
    manager.events.addListener(event, () => {
      hook.eventHook(flex, manager);
    });
  } else if (event === FlexEvent.tokenUpdated) {
    manager.events.addListener(event, (tokenPayload) => {
      hook.eventHook(flex, manager, tokenPayload);
    });
  } else if (isTaskEvent(event)) {
    manager.events.addListener(event, (task) => {
      hook.eventHook(flex, manager, task);
    });
  } else if (event === FlexEvent.workerActivityUpdated) {
    manager.events.addListener(event, (activity: Activity, allActivities: Map<string, Activity>) => {
      hook.eventHook(flex, manager, activity, allActivities);
    });
  } else if (event === FlexEvent.workerAttributesUpdated) {
    manager.events.addListener(event, (newAttributes: Record<string, any>) => {
      hook.eventHook(flex, manager, newAttributes);
    });
  }
};
