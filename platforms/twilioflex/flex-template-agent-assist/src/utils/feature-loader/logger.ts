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

import { FlexHelper } from '../helpers';
import logger from '../logger';
import Destination from '../logger/destination';

const destinations: Destination[] = [];

export const init = (manager: Flex.Manager) => {
  manager.events.addListener('flexError', (error) => {
    logger.error('Internal FlexError', error);
  });

  const worker = FlexHelper.getCurrentWorker();
  if (worker) {
    logger.addMetaData('workerSid', worker.sid);
    logger.addMetaData('workerName', worker.name);
    logger.addMetaData('source', 'twilio:flex-ui');
  }
  destinations.forEach((dest) => logger.addDestination(dest));
  logger.processBuffer();
};

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  if (!hook.loggerHook) {
    logger.warn(`Feature ${feature} declared logger hook, but is missing loggerHook to hook`);
    return;
  }

  console.info(`Feature ${feature} registered logger hook: %c${hook.loggerHook.name}`, 'font-weight:bold');
  destinations.push(hook.loggerHook());
};
