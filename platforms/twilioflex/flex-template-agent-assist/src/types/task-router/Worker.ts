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

import { WorkerAttributes } from '@twilio/flex-ui';

import Activity from './Activity';
import Reservation from './Reservation';
import Channel from './Channel';

// https://twilio.github.io/twilio-taskrouter.js/Worker.html

export default interface Worker extends EventEmitter {
  accountSid: string;
  activities: Map<string, Activity>;
  activity: Activity;
  attributes: CustomWorkerAttributes;
  channels: Map<string, Channel>;
  connectActivitySid: string;
  dateCreated: Date;
  dateStatusChanged: Date;
  dateChanged: Date;
  name: string;
  reservations: Map<string, Reservation>;
  sid: string;
  workspaceSid: string;
}

export interface CustomWorkerAttributes extends WorkerAttributes {
  SID: string;
  contact_uri: string;
  image_url: string;
  roles: ['admin' | 'supervisor' | 'agent'];

  // used for selecting language
  language?: string;

  // used to override name seen on webchat
  public_identity: string;

  // caller-id feature
  selectedCallerId: string;

  // custom-transfer-directory feature
  enforcedQueueFilter?: string;

  // Flex insights references the following elements
  email: string;
  full_name: string;
  location?: string;
  manager?: string;
  team_id?: string;
  team_name?: string;
  department_id?: string;
  department_name?: string;

  // configuration
  config_overrides?: any;
}
