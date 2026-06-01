/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Router } from 'express';
import { getHandler, patchHandler, postHandler } from '../../helpers';

const router = Router({ mergeParams: true });

const GET_ROUTES: string[] = [
  '/conversations/:conversationId', // Get conversation
  '/conversations/:conversationId/suggestions::action', // Search articles
  '/conversations/:conversationId/participants', // List participants
  '/conversations/:conversationId/participants/:participantId', // Get participant
  '/conversations/:conversationId/messages', // List participants
  '/answerRecords/:answerRecordId', // Get answer record
];

const POST_ROUTES: string[] = [
  '/conversations', // Create new conversations
  '/conversations/:conversationId/suggestions::action', // Generate summary
  '/conversations/:conversationId/participants', // Create new participant
  '/conversations/:conversationId/participants/:participantId/suggestions::action', // Suggest smart replies
  '/conversations/:conversationId/participants/:participantId::action', // Create new AnalyzeContent request
  '/answerRecords/:answerRecordId', // Create answer record
];

const PATCH_ROUTES: string[] = [
  '/answerRecords/:answerRecordId', // Patch answer record
];

for (const route of GET_ROUTES) {
  router.get(route, getHandler);
}

for (const route of POST_ROUTES) {
  router.post(route, postHandler);
}

for (const route of PATCH_ROUTES) {
  router.patch(route, patchHandler);
}

export { router as dialogflowv2beta1Router };
