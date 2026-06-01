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

import ApiService from '../../../utils/serverless/ApiService';
import { EncodedParams } from '../../../types/serverless';
import logger from '../../../utils/logger';

export interface AdminUiServiceReponse {
  configuration: any;
}

class AdminUiService extends ApiService {
  fetchUiAttributes = async (): Promise<AdminUiServiceReponse> => {
    const encodedParams: EncodedParams = {
      Token: encodeURIComponent(this.manager.user.token),
    };
    try {
      return await this.fetchJsonWithReject<AdminUiServiceReponse>(
        `${this.serverlessProtocol}://${this.serverlessDomain}/features/admin-ui/flex/fetch-config`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: this.buildBody(encodedParams),
        },
      );
    } catch (error: any) {
      logger.error(`[admin-ui] Error fetching configuration\r\n`, error);
      throw error;
    }
  };

  updateUiAttributes = async (attributesUpdate: string, mergeFeature: boolean): Promise<AdminUiServiceReponse> => {
    const encodedParams: EncodedParams = {
      Token: encodeURIComponent(this.manager.user.token),
      attributesUpdate: encodeURIComponent(attributesUpdate),
      mergeFeature: encodeURIComponent(mergeFeature),
    };
    try {
      return await this.fetchJsonWithReject<AdminUiServiceReponse>(
        `${this.serverlessProtocol}://${this.serverlessDomain}/features/admin-ui/flex/update-config`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: this.buildBody(encodedParams),
        },
      );
    } catch (error: any) {
      logger.error(`[admin-ui] Error updating configuration\r\n`, error);
      throw error;
    }
  };
}

export default new AdminUiService();
