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

import IFrameCRMTab from '../../custom-components/IFrameCRMTab';
import { FlexActionEvent } from '../../../../types/feature-loader';
import { shouldDisplayUrlWhenNoTasks, getUrlTabTitle, isUrlTabEnabled } from '../../config';

export const actionEvent = FlexActionEvent.before;
export const actionName = 'LoadCRMContainerTabs';
export const actionHook = function addURLTabToEnhancedCRM(flex: typeof Flex) {
  if (!isUrlTabEnabled()) {
    return;
  }
  flex.Actions.addListener(`${actionEvent}${actionName}`, async (payload) => {
    if (!payload.task && !shouldDisplayUrlWhenNoTasks()) {
      return;
    }

    payload.components = [
      ...payload.components,
      { title: getUrlTabTitle(), component: <IFrameCRMTab task={payload.task} key="iframe-crm-container" /> },
    ];
  });
};
