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
  { key: 'workerSid', purpose: 'unique ID of the worker' },
  {
    key: 'workerChannelSid',
    purpose: 'unique ID of the workerChannelSid to update',
  },
  { key: 'capacity', purpose: 'the new capacity' },
  { key: 'available', purpose: 'whether the channel is enabled or not' },
];

exports.handler = prepareFlexFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  try {
    // Make sure that this user is allowed to perform this action
    if (!(event.TokenResult.roles.includes('supervisor') || event.TokenResult.roles.includes('admin'))) {
      response.setStatusCode(403);
      response.setBody({ success: false, error: 'User does not have the permissions to perform this action.' });
      return callback(null, response);
    }

    const { workerSid, workerChannelSid, capacity, available } = event;
    const result = await twilioExecute(context, (client) =>
      client.taskrouter.v1
        .workspaces(process.env.TWILIO_FLEX_WORKSPACE_SID)
        .workers(workerSid)
        .workerChannels(workerChannelSid)
        .update({ capacity: Number(capacity), available: available === 'true' }),
    );
    const { status, data: workerChannelCapacity } = result;

    response.setStatusCode(status);
    response.setBody({ workerChannelCapacity, ...extractStandardResponse(result) });
    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
