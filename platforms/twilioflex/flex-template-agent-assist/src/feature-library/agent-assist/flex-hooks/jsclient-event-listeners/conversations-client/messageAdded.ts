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
import { Message } from '@twilio/conversations';

import {
  FlexJsClient,
  ConversationEvent,
  AgentAssistAction,
  invokeAgentAssistAction,
} from '../../../../../types/feature-loader';

export const clientName = FlexJsClient.conversationsClient;
export const eventName = ConversationEvent.messageAdded;
// when an agent joins a channel for the first time this announces
// them in the chat channel
export const jsClientHook = function analyzeContentRequest(flex: typeof Flex, manager: Flex.Manager, message: Message) {
  const workerIdentity = manager.store.getState().flex.session.identity;
  const conversationId = message.conversation.sid;
  const messageContent = `${message.body}`;
  const participantRole = message.author === workerIdentity ? 'HUMAN_AGENT' : 'END_USER';
  const messageSendTime = `${message.dateCreated?.toString()}`;
  const request = {
    conversationId,
    participantRole,
    request: {
      textInput: {
        text: messageContent,
        messageSendTime,
      },
    },
  };
  invokeAgentAssistAction(AgentAssistAction.analyzeContentRequest, request);
};
