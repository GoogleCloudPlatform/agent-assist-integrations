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

const { jestConfig } = require("@salesforce/sfdx-lwc-jest/config");
module.exports = {
  ...jestConfig,
  // add any custom configurations here
  testEnvironment: "jsdom",
  collectCoverageFrom: [
    // https://jestjs.io/docs/configuration#collectcoveragefrom-array
    "force-app/main/default/lwc/**/*.js",
    "!force-app/main/default/lwc/**/__tests__/**",
    "!force-app/main/default/lwc/**/*.html",
    "!force-app/main/default/lwc/**/jest.config.js",
    ...jestConfig.collectCoverageFrom
  ],
  moduleNameMapper: {
    "^lightning/logger$":
      "<rootDir>/force-app/test/jest-mocks/lightning/logger",
    "^lightning/platformResourceLoader$":
      "<rootDir>/force-app/test/jest-mocks/lightning/platformResourceLoader",
    "^lightning/conversationToolkitApi$":
      "<rootDir>/force-app/test/jest-mocks/lightning/conversationToolkitApi"
  }
};
