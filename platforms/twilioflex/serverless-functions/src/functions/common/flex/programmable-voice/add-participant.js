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

const requiredParameters = [
  { key: 'taskSid', purpose: 'unique ID of task to update' },
  { key: 'to', purpose: 'number to add to the conference' },
  { key: 'from', purpose: 'caller ID to use when adding to the conference' },
];

exports.handler = prepareFlexFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  try {
    const { taskSid, to, from } = event;

    const result = await twilioExecute(context, (client) =>
      client.conferences(taskSid).participants.create({
        to,
        from,
        earlyMedia: true,
        endConferenceOnExit: false,
      }),
    );

    response.setStatusCode(result.status);
    response.setBody({ participantsResponse: result.data, ...extractStandardResponse(result) });
    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
