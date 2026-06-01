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

import { TaskAttributes } from '../../../types/task-router/Task';
import { CustomWorkerAttributes } from '../../../types/task-router/Worker';

export interface QueueIndexItem {
  queue_sid: string;
  queue_name: string;
  workspace_sid: string;
}

export interface WorkerIndexItem {
  activity_name: string;
  attributes: CustomWorkerAttributes;
  date_activity_changed: Date;
  date_updated: Date;
  friendly_name: string;
  worker_activity_sid: string;
  worker_sid: string;
  workspace_sid: string;
}

export interface ReservationIndexItem {
  attributes: TaskAttributes;
  date_created: Date;
  date_updated: Date;
  queue_name: string;
  reservation_sid: string;
  status: string;
  task_age: number;
  task_channel_unique_name: string;
  task_date_created: Date;
  task_priority: number;
  task_sid: string;
  task_status: string;
  worker_name: string;
  worker_sid: string;
  workspace_sid: string;
}

export interface TaskIndexItem {
  accepted_reservation_sid: string;
  age: number;
  attributes: TaskAttributes;
  channel_type: string;
  channel_unique_name: string;
  date_created: Date;
  date_updated: Date;
  priority: number;
  queue_name: string;
  status: string;
  task_sid: string;
  worker_name: string;
  worker_sid: string;
  workspace_sid: string;
}
