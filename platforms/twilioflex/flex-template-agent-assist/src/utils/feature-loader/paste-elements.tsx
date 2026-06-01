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
import { CustomizationProvider, PasteCustomCSS, CustomizationProviderProps } from '@twilio-paste/core/customization';

let customPasteElements = {};

export const init = (flex: typeof Flex) => {
  // Currently the method to customize Paste elements in Flex is somewhat clunky.
  // This is correct for now but may improve. See FLEXEXP-772
  flex.setProviders({
    CustomProvider: (RootComponent) => (props) => {
      const pasteProviderProps: CustomizationProviderProps & { style: PasteCustomCSS } = {
        baseTheme: props.theme?.isLight ? 'default' : 'dark',
        theme: props.theme?.tokens,
        style: { minWidth: '100%', height: '100%' },
        elements: { ...customPasteElements },
      };
      return (
        <CustomizationProvider {...pasteProviderProps}>
          <RootComponent {...props} />
        </CustomizationProvider>
      );
    },
  });
};

export const addHook = (flex: typeof Flex, manager: Flex.Manager, feature: string, hook: any) => {
  console.info(`Feature ${feature} registered Paste element hook`);
  customPasteElements = {
    ...customPasteElements,
    ...hook.pasteElementHook,
  };
};
