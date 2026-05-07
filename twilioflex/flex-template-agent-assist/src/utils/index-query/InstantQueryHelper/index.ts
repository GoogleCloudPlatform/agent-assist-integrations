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

import { QueueIndexItem, WorkerIndexItem, ReservationIndexItem, TaskIndexItem } from './types';

enum SyncIndex {
  Task = 'tr-task',
  Worker = 'tr-worker',
  Reservation = 'tr-reservation',
  Queue = 'tr-queue',
}

export const QueueInstantQuery = async (queryExpression: string): Promise<{ [queueSid: string]: QueueIndexItem }> => {
  const { insightsClient } = Flex.Manager.getInstance();
  const query = await insightsClient.instantQuery(SyncIndex.Queue);
  return new Promise((resolve, reject) => {
    try {
      query.once('searchResult', (result) => resolve(result));
      query.search(queryExpression);
    } catch (e) {
      reject(e);
    }
  });
};

export const WorkerInstantQuery = async (
  queryExpression: string,
): Promise<{ [workerSid: string]: WorkerIndexItem }> => {
  const { insightsClient } = Flex.Manager.getInstance();
  const query = await insightsClient.instantQuery(SyncIndex.Worker);
  return new Promise((resolve, reject) => {
    try {
      query.once('searchResult', (result) => resolve(result));
      query.search(queryExpression);
    } catch (e) {
      reject(e);
    }
  });
};

export const TasksInstantQuery = async (queryExpression: string): Promise<{ [taskSid: string]: TaskIndexItem }> => {
  const { insightsClient } = Flex.Manager.getInstance();
  const query = await insightsClient.instantQuery(SyncIndex.Task);
  return new Promise((resolve, reject) => {
    try {
      query.once('searchResult', (result) => resolve(result));
      query.search(queryExpression);
    } catch (e) {
      reject(e);
    }
  });
};

export const ReservationInstantQuery = async (
  queryExpression: string,
): Promise<{ [reservationSid: string]: ReservationIndexItem }> => {
  const { insightsClient } = Flex.Manager.getInstance();
  const query = await insightsClient.instantQuery(SyncIndex.Reservation);
  return new Promise((resolve, reject) => {
    try {
      query.once('searchResult', (result) => resolve(result));
      query.search(queryExpression);
    } catch (e) {
      reject(e);
    }
  });
};
