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

import fetch from 'jest-fetch-mock';
import { resetServiceConfiguration } from './test-utils/flex-service-configuration';
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// Global test lifecycle handlers
beforeAll(() => {
  fetch.enableMocks();
});

beforeEach(() => {
  fetch.resetMocks();
})

afterEach(() => {
  resetServiceConfiguration();
});
