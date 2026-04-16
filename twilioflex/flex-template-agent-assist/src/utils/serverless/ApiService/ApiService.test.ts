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

import ApiService from '.';
import { EncodedParams } from '../../../types/serverless';
import { UIAttributes } from '../../../types/manager/ServiceConfiguration';

// NOTE: Make dummy class to extend ApiService because it's abstract
class Test extends ApiService {
  // NOTE: Make helper function to provide access to protected class members
  testHasManagerClassMember(): boolean {
    return this.manager !== undefined;
  }

  // NOTE: Make helper function to provide access to protected class members
  testBuildBody(encodedParams: EncodedParams): string {
    return this.buildBody(encodedParams);
  }
}

describe('utils/common/ApiService', () => {
  const TestService = new Test();

  it('should provide access to the Flex Manager instance', () => {
    expect(TestService.testHasManagerClassMember()).toBe(true);
  });

  it('should provide access to the configured serverless domain', () => {
    const { custom_data } = Flex.Manager.getInstance().configuration as UIAttributes;
    const { serverless_functions_domain_agent_assist, serverless_functions_port } = custom_data;
    expect(TestService.serverlessDomain).toBe(
      `${serverless_functions_domain_agent_assist}:${serverless_functions_port}`,
    );
  });

  it('should build encoded params into a string to use as the body for serverless reqeusts', () => {
    const encodedParams: EncodedParams = {
      testParam1: encodeURIComponent('testParam1ToBeEncoded'),
      testParam2: encodeURIComponent('testParam2ToBeEncoded'),
      testParamToDrop: undefined,
    };

    const body = TestService.testBuildBody(encodedParams);

    expect(body).toBe('testParam1=testParam1ToBeEncoded&testParam2=testParam2ToBeEncoded');
  });
});
