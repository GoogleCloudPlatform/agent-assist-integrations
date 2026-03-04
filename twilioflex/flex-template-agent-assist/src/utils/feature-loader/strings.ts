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

import { getUserLanguage, defaultLanguage } from '../configuration';

const userLanguage = getUserLanguage();

let customStrings = {};
let systemStrings = {};

export const init = (manager: Flex.Manager) => {
  manager.strings = {
    // -v- Add custom strings here -v-'
    ...customStrings,
    // -^---------------------------^-

    ...manager.strings,

    // -v- Modify strings provided by flex here -v-
    ...systemStrings,
    // -^----------------------------------------^-
  };
};

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  console.info(`Feature ${feature} registered string hook: %c${hook.stringHook.name}`, 'font-weight:bold');
  // Returns dictionary of language and string definitions to register
  const hookLanguages = hook.stringHook(flex, manager);
  let hookStrings = {};

  if (hookLanguages[userLanguage] && hookLanguages[defaultLanguage] && userLanguage !== defaultLanguage) {
    // Include both default and user language to allow for incomplete translations
    hookStrings = { ...hookLanguages[defaultLanguage], ...hookLanguages[userLanguage] };
  } else if (hookLanguages[defaultLanguage]) {
    hookStrings = hookLanguages[defaultLanguage];
  } else {
    console.error(
      `Feature ${feature} string hook is missing the user language (${userLanguage}) and the default language (${defaultLanguage}). Skipping.`,
    );
    return;
  }

  customStrings = {
    ...customStrings,
    ...hookStrings,
  };
};

export const addSystemHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  console.info(`Feature ${feature} registered system string hook: %c${hook.systemStringHook.name}`, 'font-weight:bold');
  // Returns dictionary of language and string definitions to register
  const hookLanguages = hook.systemStringHook(flex, manager);
  let hookStrings = {};

  if (hookLanguages[userLanguage]) {
    hookStrings = hookLanguages[userLanguage];
  } else if (hookLanguages[defaultLanguage]) {
    hookStrings = hookLanguages[defaultLanguage];
  } else {
    console.error(
      `Feature ${feature} system string hook is missing the user language (${userLanguage}) and the default language (${defaultLanguage}). Skipping.`,
    );
    return;
  }

  systemStrings = {
    ...systemStrings,
    ...hookStrings,
  };
};
