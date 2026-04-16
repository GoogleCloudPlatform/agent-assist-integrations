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

interface DestinationConstructor {
  minLogLevel: LogLevel;
  metaData?: object | null | undefined;
}

const logLevelMap = {
  debug: 0,
  log: 1,
  info: 2,
  warn: 3,
  error: 4,
};

export default abstract class Destination {
  minLogLevel: LogLevel;

  metaData?: object | null | undefined;

  // eslint-disable-next-line no-restricted-syntax
  constructor(opts: DestinationConstructor) {
    this.minLogLevel = opts.minLogLevel;
    this.metaData = opts.metaData === undefined ? {} : opts.metaData;
  }

  async log(level: LogLevel, message: string, context?: object, meta?: any): Promise<void> {
    return new Promise(async (resolve) => {
      // numeric level of current log passing through
      const levelOfCurrentLog = logLevelMap[level];
      // minimum configured log level
      const minimum = logLevelMap[this.minLogLevel];

      // only handle the log if the current destination is configured to
      if (levelOfCurrentLog >= minimum) {
        // destinations can be configured to ignore all metadata
        if (this.metaData === null) {
          await this.handle(level, message, context);
        } else {
          // merge destinations metadata if it exists with the global metadata
          // destination metadata will overwrite global if necessary
          await this.handle(level, message, context, Object.assign(meta, this.metaData));
        }
        return resolve();
      }

      return resolve();
    });
  }

  abstract handle(level: LogLevel, message: string, context?: object, meta?: object | null | undefined): Promise<void>;
}
