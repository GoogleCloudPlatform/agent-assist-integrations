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

import { EventEmitter } from 'events';

import Task from './Task';

// https://twilio.github.io/twilio-taskrouter.js/Reservation.html

export default interface Reservation extends EventEmitter {
  accountSid: string;
  dateCreated: Date;
  dateUpdated: Date;
  sid: string;
  status: 'pending' | 'accepted' | 'rejected' | 'timeout' | 'canceled' | 'rescinded' | 'wrapping' | 'completed';
  task: Task;
  task_transfer: undefined;
  timeout: number;
  workerSid: string;
  workspaceSid: string;
  accept: any;
  reject: any;
  call: any;
}
