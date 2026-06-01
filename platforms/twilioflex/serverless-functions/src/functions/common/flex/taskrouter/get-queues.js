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

const requiredParameters = [];

exports.handler = prepareFlexFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  try {
    const result = await twilioExecute(context, (client) =>
      client.taskrouter.v1.workspaces(process.env.TWILIO_FLEX_WORKSPACE_SID).taskQueues.list({ limit: 1000 }),
    );
    const { data: fullQueueData, status } = result;
    const queues = fullQueueData
      ? fullQueueData.map((queue) => {
          const { targetWorkers, friendlyName, sid } = queue;
          return { targetWorkers, friendlyName, sid };
        })
      : null;
    response.setStatusCode(status);
    response.setBody({ queues, ...extractStandardResponse(result) });
    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
