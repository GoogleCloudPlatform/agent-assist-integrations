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

import { SyncClient, SyncMap } from 'twilio-sync';

import Sync, { getAllSyncMapItems } from './SyncClient';

describe('sdk-clients/SyncClient', () => {
  it('should create a SyncClient instance', () => {
    expect(Sync instanceof SyncClient).toBe(true);
  });

  describe('getAllSyncMapItems', () => {
    it('should load and return all of paginated data', async () => {
      const data = [
        { key: 'testSid1', value: {} },
        { key: 'testSid2', value: {} },
      ];
      const syncMap = {
        getItems: async () => ({
          hasNextPage: true,
          items: [data[0]],
          nextPage: async () => ({ hasNextPage: false, items: [data[1]] }),
        }),
      } as SyncMap;
      expect(await getAllSyncMapItems(syncMap)).toEqual(data);
    });
  });
});
