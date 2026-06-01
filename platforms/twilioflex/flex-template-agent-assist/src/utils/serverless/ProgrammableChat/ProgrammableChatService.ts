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

import { EncodedParams } from '../../../types/serverless';
import ApiService from '../ApiService';

export interface UpdateChannelAttributesResponse {
  success: boolean;
}

class ProgrammableChatService extends ApiService {
  async updateChannelAttributes(channelSid: string, attributes: any): Promise<boolean> {
    try {
      const { success } = await this.#updateChannelAttributes(channelSid, JSON.stringify(attributes));
      return success;
    } catch (error) {
      return false;
    }
  }

  #updateChannelAttributes = async (channelSid: string, attributes: any): Promise<UpdateChannelAttributesResponse> => {
    const manager = Flex.Manager.getInstance();

    const encodedParams: EncodedParams = {
      Token: encodeURIComponent(manager.user.token),
      channelSid: encodeURIComponent(channelSid),
      attributes: encodeURIComponent(attributes),
    };

    return this.fetchJsonWithReject<UpdateChannelAttributesResponse>(
      `${this.serverlessProtocol}://${this.serverlessDomain}/common/flex/programmable-chat/update-channel-attributes`,
      {
        method: 'post',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: this.buildBody(encodedParams),
      },
    ).then((response): UpdateChannelAttributesResponse => {
      return {
        ...response,
      };
    });
  };
}

export default new ProgrammableChatService();
