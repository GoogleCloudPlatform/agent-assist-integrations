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

const { prepareFlexFunction, extractStandardResponse } = require(Runtime.getFunctions()[
  'common/helpers/function-helper'
].path);
const Configuration = require(Runtime.getFunctions()['common/twilio-wrappers/configuration'].path);

const requiredParameters = [];

exports.handler = prepareFlexFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  try {
    const result = await Configuration.fetchUiAttributes({
      context,
    });

    const { data: configuration } = result;
    response.setStatusCode(result.status);
    response.setBody({ configuration, ...extractStandardResponse(result) });

    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
