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

import { Action as ReduxAction } from 'redux';

// Extend this payload to be of type that your ReduxAction is
// Normally you'd follow this pattern...https://redux.js.org/recipes/usage-with-typescript#a-practical-example
// But that breaks the typing when adding the reducer to Flex, so no payload intellisense for you!
export default interface Action extends ReduxAction {
  payload?: any;
}
