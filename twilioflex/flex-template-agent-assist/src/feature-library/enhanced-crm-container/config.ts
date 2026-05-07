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
import EnhancedCRMContainerConfig from './types/ServiceConfiguration';

const {
  enabled = false,
  enable_url_tab = false,
  url_tab_title = '',
  url = '',
  should_display_url_when_no_tasks = false,
  display_url_when_no_tasks = '',
} = (getFeatureFlags()?.features?.enhanced_crm_container as EnhancedCRMContainerConfig) || {};

export const isFeatureEnabled = () => {
  return enabled;
};

export const shouldDisplayUrlWhenNoTasks = () => {
  return should_display_url_when_no_tasks;
};

export const displayUrlWhenNoTasks = () => {
  return display_url_when_no_tasks;
};

export const getUrl = () => {
  return url;
};

export const isUrlTabEnabled = () => {
  return enable_url_tab;
};

export const getUrlTabTitle = () => {
  return url_tab_title;
};
