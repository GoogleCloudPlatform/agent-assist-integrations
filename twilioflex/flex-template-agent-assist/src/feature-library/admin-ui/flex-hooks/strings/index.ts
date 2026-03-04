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

import esES from './es-es.json';
import esMX from './es-mx.json';
import ptBR from './pt-br.json';
import th from './th.json';
import zhHans from './zh-hans.json';

export enum StringTemplates {
  ADMIN_TITLE = 'PSAdminTitle',
  CONFIG_FOR_TITLE = 'PSAdminConfigForTitle',
  CONFIG_FOR_MYSELF = 'PSAdminConfigForMyself',
  CONFIG_FOR_EVERYONE = 'PSAdminConfigForEveryone',
  ENABLED = 'PSAdminEnabled',
  DISABLED = 'PSAdminDisabled',
  DOCS = 'PSAdminDocs',
  REVERT_WORKER_TO_GLOBAL = 'PSAdminRevertWorkerToGlobal',
  MORE_SETTINGS = 'PSAdminMoreSettings',
  NO_MORE_SETTINGS = 'PSAdminNoMoreSettings',
  FILTER_FEATURES = 'PSAdminFilterFeatures',
  MODAL_SETTINGS_TITLE = 'PSAdminModalSettingsTitle',
  SAVE_ERROR = 'PSAdminSaveError',
  SAVE_SUCCESS = 'PSAdminSaveSuccess',
  INVALID_JSON = 'PSAdminInvalidJson',
  UPDATED_MODAL_TITLE = 'PSAdminUpdatedModalTitle',
  UPDATED_MODAL_DESC = 'PSAdminUpdatedModalDesc',
  UPDATED_MODAL_RELOAD = 'PSAdminUpdatedModalReload',
  SAVE_DISABLED = 'PSAdminSaveDisabled',
  EDIT_COMMON_SETTINGS = 'PSAdminEditCommonSettings',
  MISSING_SETTINGS = 'PSAdminMissingSettings',
}

export const stringHook = () => ({
  'en-US': {
    [StringTemplates.ADMIN_TITLE]: 'Feature Settings',
    [StringTemplates.CONFIG_FOR_TITLE]: 'Configure for:',
    [StringTemplates.CONFIG_FOR_MYSELF]: 'Myself',
    [StringTemplates.CONFIG_FOR_EVERYONE]: 'Everyone',
    [StringTemplates.ENABLED]: 'Enabled',
    [StringTemplates.DISABLED]: 'Disabled',
    [StringTemplates.DOCS]: 'Docs',
    [StringTemplates.REVERT_WORKER_TO_GLOBAL]: 'Revert to global setting',
    [StringTemplates.MORE_SETTINGS]: 'More settings',
    [StringTemplates.NO_MORE_SETTINGS]: 'This feature has no additional settings',
    [StringTemplates.FILTER_FEATURES]: 'Filter features...',
    [StringTemplates.MODAL_SETTINGS_TITLE]: '{{feature}} settings',
    [StringTemplates.SAVE_ERROR]: 'There was an error saving the changes. Please try again.',
    [StringTemplates.SAVE_SUCCESS]: 'Changes saved successfully. Reload Flex for changes to take effect.',
    [StringTemplates.INVALID_JSON]: 'Enter valid JSON in order to save.',
    [StringTemplates.UPDATED_MODAL_TITLE]: 'Settings updated',
    [StringTemplates.UPDATED_MODAL_DESC]:
      'Another user has updated global settings. Click "Reload" to refresh the view with the updated settings. Saving global settings will be unavailable until the view is reloaded.',
    [StringTemplates.UPDATED_MODAL_RELOAD]: 'Reload',
    [StringTemplates.SAVE_DISABLED]: 'Saving global settings is unavailable until the view is reloaded.',
    [StringTemplates.EDIT_COMMON_SETTINGS]: 'Edit common settings',
    [StringTemplates.MISSING_SETTINGS]:
      'No settings were found. This could be due to them being removed or not yet deployed.',
  },
  'es-MX': esMX,
  'pt-BR': ptBR,
  th,
  'zh-Hans': zhHans,
  'es-ES': esES,
});
