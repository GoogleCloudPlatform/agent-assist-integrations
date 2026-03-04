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

import { Conversation, Message, Participant, Paginator } from '@twilio/conversations';

interface ParticipantState {
  readonly source: Participant;
  readonly friendlyName: string;
  readonly online: boolean;
}
type ParticipantType = Map<string, ParticipantState>;

interface MessageState {
  readonly isFromMe: boolean;
  readonly groupWithNext: boolean;
  readonly groupWithPrevious: boolean;
  readonly index: number;
  readonly authorName?: string;
  readonly isSending?: boolean;
  readonly error?: boolean;
  readonly bodyAttachment?: string;
}

export default interface ConversationState {
  readonly currentPaginator?: Paginator<Message>;
  readonly isLoadingMessages: boolean;
  readonly isLoadingParticipants: boolean;
  readonly lastReadMessageIndex: number;
  readonly lastReadMessageByCurrentUserIndex: number;
  readonly participants: ParticipantType;
  readonly unreadMessages: MessageState[];
  readonly messages: MessageState[];
  readonly pendingMessages: MessageState[];
  readonly source?: Conversation;
  readonly typers: ParticipantState[];
  readonly isLoadingConversation: boolean;
  readonly errorWhileLoadingConversation: boolean;
  readonly showScrollDownBtn: boolean;
  readonly lastScrollPosition: number;
}
