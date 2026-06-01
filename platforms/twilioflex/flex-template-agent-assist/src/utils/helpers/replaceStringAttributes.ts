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

import { ITask, Manager } from '@twilio/flex-ui';

import ApiService from '../serverless/ApiService';

class ReplaceStringService extends ApiService {
  serverlessUrl = `${this.serverlessProtocol}://${this.serverlessDomain}`;
}

const replaceStringServiceInstance = new ReplaceStringService();

/**
 * This function accepts a string and performs templatized replacement of task attributes, worker attributes, and serverless domains
 * @param {string} text - Templatized input string
 * @param {ITask} task - Task from which to source attributes
 * @returns {string}  - The transformed string
 */
export default (text: string, task?: ITask): string => {
  return text.replace(/{{(task|worker|serverless)\.((\w|\.)+)}}/g, (match: string, part1: string, part2: string) => {
    // this runs for each match found

    let attributes;

    if (part1 === 'task' && task) {
      attributes = task.attributes;
    } else if (part1 === 'worker') {
      attributes = Manager.getInstance().workerClient?.attributes;
    } else if (part1 === 'serverless') {
      return replaceStringServiceInstance.serverlessUrl;
    } else {
      return match;
    }

    return part2.split('.').reduce((accumulator: any, current, _index, array) => {
      if (!accumulator[current]) {
        // abort early by removing the rest of the array
        array.splice(1);
        return '';
      }
      return accumulator[current];
    }, attributes);
  });
};
