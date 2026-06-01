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

const { prepareStudioFunction, extractStandardResponse } = require(Runtime.getFunctions()[
  'common/helpers/function-helper'
].path);
const TaskRouterOperations = require(Runtime.getFunctions()['common/twilio-wrappers/taskrouter'].path);

const requiredParameters = [
  { key: 'workflowSid', purpose: 'workflow to execute' },
  { key: 'taskChannel', purpose: 'task channel for task' },
  { key: 'attributes', purpose: 'attributes for task' },
];

exports.handler = prepareStudioFunction(requiredParameters, async (context, event, callback, response, handleError) => {
  try {
    const { workflowSid, taskChannel, attributes, priority, timeout } = event;

    const result = await TaskRouterOperations.createTask({
      context,
      workflowSid,
      taskChannel,
      attributes: JSON.parse(attributes),
      priority,
      timeout,
    });

    const { data: task, status } = result;

    response.setStatusCode(status);
    response.setBody({ task, taskSid: task.sid, ...extractStandardResponse(result) });
    return callback(null, response);
  } catch (error) {
    return handleError(error);
  }
});
