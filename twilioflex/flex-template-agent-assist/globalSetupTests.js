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

import 'regenerator-runtime/runtime';

module.exports = async () => {
  // NOTE: This is needed to set the TZ in azure build pipeline
  //       BUT, it doesn't work on windows so build.yaml should use a linux image
  //       https://stackoverflow.com/a/56482581
  
  // CAVEAT: Developers using windows need to be in this timezone when running unit tests for date based unit tests to pass
  //         https://github.com/nodejs/node/issues/4230
  process.env.TZ = 'America/New_York';
};