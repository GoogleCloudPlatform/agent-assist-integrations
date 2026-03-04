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

import { Radio, RadioGroup } from '@twilio-paste/core/radio-group';
import { Switch } from '@twilio-paste/core/switch';
import { FormControl } from '@twilio-paste/core/form';

import { Transcription } from '../../../types/ServiceConfiguration';

interface SwitchWithOptionsProps {
  isEnabled: boolean;
  featureLabel: string;
  featureChangeHandler: any;
  featureDisabled?: boolean;
  featureOptions: {
    value: string;
    helpText: string;
    label: string;
    defaultChecked?: boolean;
  }[];
  optionsChangeHandler: any;
  optionsDisabled: boolean;
}

export const SwitchWithOptions = ({
  isEnabled,
  featureLabel,
  featureChangeHandler,
  featureOptions,
  featureDisabled,
  optionsDisabled,
  optionsChangeHandler,
}: SwitchWithOptionsProps): JSX.Element => {
  return (
    <Switch
      checked={isEnabled}
      onChange={(e) => featureChangeHandler()}
      data-testid={`enable-${featureLabel}-switch`}
      disabled={featureDisabled}
      helpText={
        <FormControl key={`${featureLabel}-version`}>
          <RadioGroup
            legend={<></>}
            name={`${featureLabel}-version`}
            data-testid={`${featureLabel}-version-radio-group`}
            disabled={optionsDisabled}
            onChange={(e) => optionsChangeHandler(e)}
          >
            {featureOptions.map((feature) => {
              const { label, ...props } = feature;
              return <Radio {...props}>{label}</Radio>;
            })}
          </RadioGroup>
        </FormControl>
      }
    >
      {featureLabel}
    </Switch>
  );
};
