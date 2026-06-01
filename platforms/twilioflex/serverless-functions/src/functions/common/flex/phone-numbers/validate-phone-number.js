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

const { prepareFlexFunction, extractStandardResponse, twilioExecute } = require(Runtime.getFunctions()[
  'common/helpers/function-helper'
].path);

const requiredParameters = [{ key: 'phoneNumber', purpose: 'phone number to validate' }];

exports.handler = prepareFlexFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  const { phoneNumber } = event;

  try {
    const result = await twilioExecute(context, (client) => client.lookups.v2.phoneNumbers(phoneNumber).fetch());
    const { data: lookupResponse, status } = result;
    let { valid } = lookupResponse;
    let invalidReason = null;

    if (valid) {
      // Number is valid, check if we are allowed to dial it
      const { data: permissionsResponse } = await twilioExecute(context, (client) =>
        client.voice.v1.dialingPermissions.countries(lookupResponse.countryCode).fetch(),
      );

      if (!permissionsResponse.lowRiskNumbersEnabled) {
        valid = false;
        invalidReason = 'COUNTRY_DISABLED';
      } else if (!permissionsResponse.highRiskSpecialNumbersEnabled) {
        // Check if this number is considered a high-risk special number
        const { data: highRiskResponse } = await twilioExecute(context, (client) =>
          client.voice.v1.dialingPermissions.countries(lookupResponse.countryCode).highriskSpecialPrefixes.list(),
        );
        const normalizedNumber = phoneNumber.replace('+', '');
        const matchedPrefix = highRiskResponse?.filter((item) =>
          normalizedNumber.startsWith(item.prefix.replace('+', '')),
        );

        if (matchedPrefix?.length) {
          valid = false;
          invalidReason = 'HIGH_RISK_SPECIAL_NUMBER_DISABLED';
        }
      }
    } else {
      invalidReason = lookupResponse.validationErrors?.join(', ');
    }

    response.setStatusCode(status);
    response.setBody({ valid, invalidReason, ...extractStandardResponse(result) });
    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
