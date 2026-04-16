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

import { Manager } from '@twilio/flex-ui';

import SyncClient from '../sdk-clients/sync/SyncClient';
import { getFeatureFlags } from '../configuration';
import logger from '../logger';

const AUDIT_LIST_PREFIX = 'AuditLog';
const { audit_log_ttl = 1209600 } = getFeatureFlags().common || {};

const performSave = async (feature: string, data: any) => {
  const list = await SyncClient.list(`${AUDIT_LIST_PREFIX}_${feature}`);
  await list.push(data, { ttl: audit_log_ttl });
};

export const saveAuditEvent = async (feature: string, event: string, oldValue?: any, newValue?: any) => {
  const data = {
    timestamp: new Date().toString(),
    worker: Manager.getInstance().workerClient?.name ?? 'Unknown',
    event,
    oldValue,
    newValue,
  };

  // Validate that the data does not exceed 16 KiB
  if (data.oldValue || data.newValue) {
    const size = new Blob([JSON.stringify(data)]).size;
    if (size >= 16384) {
      data.oldValue = 'Removed due to excessive size';
      data.newValue = 'Removed due to excessive size';
    }
  }

  try {
    await performSave(feature, data);
  } catch (error: any) {
    logger.error('[AuditHelper] Retrying audit event save due to error.', error);
    await performSave(feature, data);
  }
};
