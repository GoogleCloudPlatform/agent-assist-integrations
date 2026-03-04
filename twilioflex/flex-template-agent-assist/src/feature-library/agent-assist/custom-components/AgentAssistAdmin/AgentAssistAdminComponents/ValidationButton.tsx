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

import { HelpText } from '@twilio-paste/core/help-text';
import { Button } from '@twilio-paste/core/button';
import { Stack } from '@twilio-paste/core/stack';

interface ConfigItem {
  configItem: string;
  hasError: boolean;
  statusMessage: string;
}

interface ValidationButtonProps {
  configItem: ConfigItem;
  testConnectionFunction: any;
  label: string;
  dataTestId: string;
}

export const ValidationButton = ({
  configItem,
  testConnectionFunction,
  label,
  dataTestId,
}: ValidationButtonProps): JSX.Element => {
  return (
    <Stack orientation="horizontal" spacing="space30">
      <Button
        variant="primary"
        onClick={(e) => testConnectionFunction()}
        disabled={configItem.configItem === '' || configItem.hasError}
        data-testid={dataTestId}
      >
        {label}
      </Button>
      {configItem.statusMessage !== '' && (
        <HelpText id="endpoint-help-text" variant={configItem.hasError ? 'error' : 'success'}>
          {configItem.statusMessage}
        </HelpText>
      )}
    </Stack>
  );
};
