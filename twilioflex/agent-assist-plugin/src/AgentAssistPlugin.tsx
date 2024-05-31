/**
 * Copyright 2024 Google LLC
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

import React from 'react';
import * as Flex from '@twilio/flex-ui';
import {FlexPlugin} from '@twilio/flex-plugin';
import AgentAssistContainer from './components/AgentAssistContainer';

const PLUGIN_NAME = 'AgentAssistPlugin';
const config = {
  CONVERSATION_PROFILE:`${process.env.TWILIO_CONVERSATION_PROFILE}`,
  FEATURES: `${process.env.TWILIO_FEATURES}`,
  DEBUG: `${process.env.TWILIO_DEBUG}`,
  FUNCTIONS_URL:`${process.env.TWILIO_FUNCTIONS_URL}`
}



export default class AgentAssistPlugin extends FlexPlugin {
  constructor() {
    super(PLUGIN_NAME);
  }


  /**
   * This code is run when your plugin is being started
   * Use this to modify any UI components or attach to the actions framework
   *
   * @param flex { typeof Flex }
   */
  async init(flex: typeof Flex, manager: Flex.Manager): Promise<void> {
    console.log(config)
    flex.CRMContainer.Content.replace(<AgentAssistContainer key='agent-assist'/>)
  }
}
