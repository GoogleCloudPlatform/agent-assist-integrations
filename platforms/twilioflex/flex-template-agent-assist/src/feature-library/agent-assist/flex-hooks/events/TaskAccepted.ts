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
import { ITask } from '@twilio/flex-ui';

import { FlexEvent, AgentAssistAction, invokeAgentAssistAction } from '../../../../types/feature-loader';
import AgentAssistUtils from '../../utils/agentAssist/AgentAssistUtils';
import logger from '../../../../utils/logger';

async function selectAndAcceptTask(task: ITask) {
  const { sid, taskChannelUniqueName, attributes } = task;
  const agentAssistUtils = AgentAssistUtils.instance;
  let conversationSid;

  if (task !== undefined) {
    if (taskChannelUniqueName === 'voice') {
      conversationSid = task.attributes.call_sid;
    } else {
      conversationSid = Flex.TaskHelper.getTaskConversationSid(task);
    }

    logger.debug(`[Agent-Assist] Setting active conversation to ${conversationSid}`);

    const conversationName = agentAssistUtils.getConversationName(`${conversationSid}`);
    const request = {
      conversationName,
    };
    invokeAgentAssistAction(AgentAssistAction.activeConversationSelected, request);

    if (Flex.TaskHelper.isCallTask(task ?? Flex.TaskHelper.getTaskByTaskSid(conversationSid))) {
      console.log(`[Agent-Assist] Listening for suggestions to conversation ${conversationName}`);
      try {
        agentAssistUtils.subscribeToConversation(conversationName);
      } catch (e: any) {
        logger.debug(e);
      }
    }
  }
}

export const eventName = FlexEvent.taskAccepted;
export const eventHook = function selectAndAcceptTaskHook(flex: typeof Flex, manager: Flex.Manager, task: ITask) {
  selectAndAcceptTask(task);
};
