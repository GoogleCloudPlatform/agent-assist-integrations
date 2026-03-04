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

import { getFeatureFlags } from '../../utils/configuration';
import FEATURE_CLASS_NAMEConfig from './types/ServiceConfiguration';

const { enabled = false } = (getFeatureFlags()?.features?.FEATURE_CONFIG_NAME as FEATURE_CLASS_NAMEConfig) || {};

export const isFeatureEnabled = () => {
  return enabled;
};
