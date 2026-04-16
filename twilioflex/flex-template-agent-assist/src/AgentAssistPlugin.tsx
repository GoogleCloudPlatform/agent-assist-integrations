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
import { FlexPlugin } from '@twilio/flex-plugin';
import loadjs from 'loadjs';

import { getScriptSources } from './feature-library/agent-assist/config';
import { initFeatures, initAgentAssistFeatures } from './utils/feature-loader';

const PLUGIN_NAME = 'AgentAssist';

export default class AgentAssist extends FlexPlugin {
  // eslint-disable-next-line no-restricted-syntax
  constructor() {
    super(PLUGIN_NAME);
  }

  /**
   * This code is run when your plugin is being started
   * Use this to modify any UI components or attach to the actions framework
   *
   * @param flex { typeof Flex }
   * @param manager { Flex.Manager }
   */
  init(flex: typeof Flex, manager: Flex.Manager) {
    const scriptSources = Object.values(getScriptSources());
    loadjs(scriptSources, 'agent-assist');
    loadjs.ready('agent-assist', function () {
      initAgentAssistFeatures(flex, manager);
    });
    initFeatures(flex, manager);
  }
}
