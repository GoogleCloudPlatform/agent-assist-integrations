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

import { PasteCustomCSS } from '@twilio-paste/customization';

export const pasteElementHook = {
  CRM_TAB_PANEL: {
    overflowY: 'scroll',
    display: 'flex',
    flex: '1 0 auto',
    width: '100%',
    borderRadius: 'borderRadius0',
  },
  CRM_TAB_PANELS: {
    display: 'flex',
    flex: '1 0 auto',
    width: '100%',
  },
  CRM_TABS: {
    display: 'flex',
    flex: '1 0 auto',
    flexDirection: 'column',
    width: '100%',
  },
  CRM_TAB_LIST_CHILD: {
    marginBottom: 'space0',
  },
  CRM_FLEX: {
    alignItems: 'stretch',
    overflow: 'auto',
  },
} as { [key: string]: PasteCustomCSS };
