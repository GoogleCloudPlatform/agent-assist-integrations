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

import { StringTemplates } from '../strings';

// Export the notification IDs an enum for better maintainability when accessing them elsewhere
export enum AdminUiNotification {
  SAVE_ERROR = 'PSAdminSaveError',
  SAVE_SUCCESS = 'PSAdminSaveSuccess',
  SAVE_DISABLED = 'PSAdminSaveDisabled',
}

// Return an array of Flex.Notification
export const notificationHook = (flex: typeof Flex, _manager: Flex.Manager) => [
  {
    id: AdminUiNotification.SAVE_ERROR,
    type: flex.NotificationType.error,
    content: StringTemplates.SAVE_ERROR,
    timeout: 3000,
    closeButton: true,
  },
  {
    id: AdminUiNotification.SAVE_SUCCESS,
    type: flex.NotificationType.success,
    content: StringTemplates.SAVE_SUCCESS,
    timeout: 3000,
    closeButton: true,
  },
  {
    id: AdminUiNotification.SAVE_DISABLED,
    type: flex.NotificationType.warning,
    content: StringTemplates.SAVE_DISABLED,
    timeout: 0,
    closeButton: false,
  },
];
