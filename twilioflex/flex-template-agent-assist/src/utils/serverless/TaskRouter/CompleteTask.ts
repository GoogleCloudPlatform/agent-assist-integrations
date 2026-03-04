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

import { FlexActionEvent, FlexAction } from '../../../types/feature-loader';
import TaskRouterService from './TaskRouterService';

export const actionEvent = FlexActionEvent.replace;
export const actionName = FlexAction.CompleteTask;
export const actionHook = function updatePendingTaskAttributesAtCompleteTask(
  flex: typeof Flex,
  _manager: Flex.Manager,
) {
  flex.Actions.replaceAction(`${actionName}`, async (payload, original) => {
    // Execute any pending task attribute updates
    if (payload.task?.taskSid) {
      await TaskRouterService.updateTaskAttributes(payload.task.taskSid, {});
    }

    // Carry on
    original(payload);
  });
};
