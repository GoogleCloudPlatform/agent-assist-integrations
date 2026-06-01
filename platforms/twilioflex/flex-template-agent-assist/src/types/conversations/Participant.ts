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

export type ParticipantInviteType = 'Worker' | 'Queue';

export type ParticipantType = 'agent' | 'worker';

export interface WorkerParticipantInvite {
  full_name: string;
  activity_name: string;
  worker_sid: string;
  available: boolean;
}

export interface QueueParticipantInvite {
  queue_name: string;
  queue_sid: string;
}

export interface ParticipantInvite {
  type: ParticipantInviteType;
  participant: WorkerParticipantInvite | QueueParticipantInvite | null;
}

export interface InvitedParticipantDetails {
  invitesTaskSid: string;
  targetSid: string;
  targetName: string;
  timestampCreated: Date;
  inviteTargetType: ParticipantInviteType;
}

export interface InvitedParticipants {
  invites: (InvitedParticipantDetails | undefined)[];
}

export interface ParticipantDetails {
  friendlyName: string;
  participantType: ParticipantType;
  isMe: boolean;
  interactionParticipantSid: string;
  conversationMemberSid: string;
}
