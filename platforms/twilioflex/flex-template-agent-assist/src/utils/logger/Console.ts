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

import { LogLevel } from '.';
import Destination from './destination';

export default class Console extends Destination {
  async handle(level: LogLevel, message: string, context?: object, meta?: object): Promise<void> {
    return new Promise((resolve) => {
      let additonalContext: object = {};
      additonalContext = Object.assign(additonalContext, meta, context);

      // if there is additional context, use it
      if (Object.keys(additonalContext).length) {
        console[level](message, additonalContext);
      } else {
        console[level](message);
      }

      return resolve();
    });
  }
}
