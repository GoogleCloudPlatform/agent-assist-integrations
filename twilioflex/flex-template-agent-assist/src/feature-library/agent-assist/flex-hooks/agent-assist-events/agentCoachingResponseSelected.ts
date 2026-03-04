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

import { AgentAssistEvent } from '../../../../types/feature-loader';
import logger from '../../../../utils/logger';

export const agentAssistEventName = AgentAssistEvent.agentCoachingResponseSelected;
export const agentAssistEventHook = function populateMessageInputWithAgentCoachingSuggestion(
  _flex: typeof Flex,
  _manager: Flex.Manager,
  event: any,
) {
  const taskSid = _flex.Manager.getInstance().store.getState().flex.view.selectedTaskSid;
  if (taskSid) {
    const task = _flex.TaskHelper.getTaskByTaskSid(taskSid);
    const conversationSid = _flex.TaskHelper.getTaskConversationSid(task);
    const suggestion = event.detail.selectedResponse;
    logger.debug('[agent-assist][agent-coaching] Setting agent coaching suggestion into message box');
    _flex.Actions.invokeAction('SetInputText', {
      body: suggestion,
      conversationSid,
      selectionStart: suggestion.length,
      selectionEnd: suggestion.length,
    });
  }
};
