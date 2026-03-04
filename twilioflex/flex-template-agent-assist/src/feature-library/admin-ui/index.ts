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

import { Actions } from '@twilio/flex-ui';

import { FeatureDefinition } from '../../types/feature-loader';
import { isFeatureEnabled } from './config';
// @ts-ignore
import hooks from './flex-hooks/**/*.*';
// @ts-ignore
import adminHooks from '../*/admin-hook.tsx';

export const register = (): FeatureDefinition => {
  if (!isFeatureEnabled()) return {};

  // load other features' admin hooks
  const adminHooksArr = typeof adminHooks === 'undefined' ? [] : adminHooks;
  const adminEvent = 'beforeOpenFeatureSettings';
  for (const adminHook of adminHooksArr) {
    if (!adminHook.adminHook) {
      continue;
    }
    Actions.addListener(adminEvent, async (payload, _abortFunction) => {
      adminHook.adminHook(payload);
    });
    console.info(
      `Feature admin-ui registered %c${adminEvent} %caction hook: %c${adminHook.adminHook.name}`,
      'font-weight:bold',
      'font-weight:normal',
      'font-weight:bold',
    );
  }

  return { name: 'admin-ui', hooks: typeof hooks === 'undefined' ? [] : hooks };
};
